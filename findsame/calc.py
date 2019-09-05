"""
python < v3.6
-------------

In order to guarantee consistent output between two runs on the same data, we
use OrderedDict. As of Python 3.7, builtin dicts are ordered again. Already in
3.6, this was an implementation detail of CPython. Before, some Python versions
had random order dicts, some did not, but it was never in the spec. Still, we
use OrderedDict to support older Pythons.

Even with OrderedDict(), the output order is different from the
python2-generated ordered ref_output in test/. To make tests pass, we need to
sort the output, as well as the ref_output generated with python2.
"""

import os
import hashlib
import functools
import itertools
from collections import defaultdict
##from multiprocessing import Pool # same as ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from findsame import common as co
from findsame.parallel import ProcessAndThreadPoolExecutor, \
    SequentialPoolExecutor
from findsame.config import cfg

HASHFUNC = hashlib.sha1


def hashsum(x):
    """Hash of a string. Uses HASHFUNC."""
    return HASHFUNC(x.encode()).hexdigest()


def hash_file(fn, blocksize=None):
    """Hash file content. Same as::

        $ sha1sum <filename>

    Parameters
    ----------
    fn : str
        filename
    blocksize : int
        size of block (bytes) to read at once

    Notes
    -----
    idea stolen from: http://pythoncentral.io/hashing-files-with-python/

    blocksize : avoid reading a big file completely into memory, blocksize=1
        MiB is fastest, tested on Core i3, hash 500 MiB file, ~ 1s, sha1sum ~
        1.5s
    """
    hasher = HASHFUNC()
    with open(fn, 'rb') as fd:
        buf = fd.read(blocksize)
        while buf:
            hasher.update(buf)
            buf = fd.read(blocksize)
    return hasher.hexdigest()


def adjust_blocksize(blocksize, limit):
    """Calculate a new `blocksize` that fits `limit` (size and modulo) such that we
    never read beyond `limit`.

    Parameters
    ----------
    blocksize : int
    limit : int

    Returns
    -------
    bs : int
        new blocksize

    Note
    ----
    This function is slow and shall not be used in inner loops. That's why we
    have :func:`hash_file_limit` for interactive use and
    :func:`hash_file_limit_core` for inner loops.
    """
    bs = blocksize
    li = limit
    if li is not None:
        assert li > 0, "limit must be > 0"
        bs = li if bs > li else bs
        if bs < li:
            while li % bs != 0:
                bs -= 1
            assert bs > 0
    return bs


def hash_file_limit(fn, blocksize=None, limit=None):
    """Same as :func:`hash_file`, but stop at approximately `limit` bytes.

    Slow reference implementation b/c of :func:`adjust_blocksize`. In production,
    use `hash_file_limit_core`.
    """
    return hash_file_limit_core(fn, adjust_blocksize(blocksize, limit), limit)


def hash_file_limit_core(fn, blocksize=None, limit=None):
    # These tests need to be here. Timing shows that they cost virtually
    # nothing. Only adjust_blocksize() is slow and was thus moved out.
    assert blocksize is not None and (blocksize > 0)
    assert (limit is not None) and (limit > 0)
    if blocksize < limit:
        assert limit % blocksize == 0
    else:
        assert blocksize % limit == 0
    hasher = HASHFUNC()
    size = 0
    with open(fn, 'rb') as fd:
        buf = fd.read(blocksize)
        size += len(buf)
        while buf and size <= limit:
            hasher.update(buf)
            buf = fd.read(blocksize)
            size += len(buf)
    return hasher.hexdigest()


def split_path(path):
    """//foo/bar/baz -> ['foo', 'bar', 'baz']"""
    return [x for x in path.split('/') if x != '']


# Merkle tree
#
# node = dir
# leaf = file
#
# In [38]: !tree test
# test                      # top node
# └── a                     # node
#     ├── b                 # node
#     │   ├── c             # node
#     │   │   └── file1     # leaf
#     │   ├── file4         # leaf
#     │   └── file5         # leaf
#     ├── d                 # node
#     │   └── e             # node
#     │       └── file2     # leaf
#     └── file3             # leaf
#
# 5 directories, 5 files
#
# In [39]: [(r,d,f) for r,d,f in os.walk('test/')]
# Out[39]:
# [('test/', ['a'], []),
#  ('test/a', ['b', 'd'], ['file3']),
#  ('test/a/b', ['c'], ['file5', 'file4']),
#  ('test/a/b/c', [], ['file1']),
#  ('test/a/d', ['e'], []),
#  ('test/a/d/e', [], ['file2'])]

class Element:
    def __init__(self, path=None):
        self.kind = None
        self.path = path

    def __repr__(self):
        return f"{self.kind}:{self.path}"

    @co.lazyprop
    def fpr(self):
        co.debug_msg(f"fpr: {self.path}")
        return self._get_fpr()

    def _get_fpr(self):
        raise NotImplementedError


class Node(Element):
    def __init__(self, *args, childs=None, **kwds):
        super().__init__(*args, **kwds)
        self.kind = 'node'
        self.childs = childs

    def add_child(self, child):
        self.childs.append(child)

    @staticmethod
    def _merge_fpr(fpr_lst):
        """Hash of a list of fpr strings. Sort them first to ensure reproducible
        results."""
        nn = len(fpr_lst)
        if nn > 1:
            return hashsum(''.join(sorted(fpr_lst)))
        elif nn == 1:
            return fpr_lst[0]
        # no childs, this happen if
        # * we really have a node (=dir) w/o childs
        # * we have only links in the dir .. we currently treat
        #   that dir as empty since we ignore links
        else:
            return hashsum('')

    def _get_fpr(self):
        return self._merge_fpr([c.fpr for c in self.childs])


class Leaf(Element):
    def __init__(self, *args, fpr_func=hash_file, **kwds):
        super().__init__(*args, **kwds)
        self.kind = 'leaf'
        self.fpr_func = fpr_func

    def _get_fpr(self):
        return self.fpr_func(self.path)


# XXX check whether we can change leafs and nodes from dict to a list, I think
# we never iterate over the dict and use the keys (which is path, also in each
# Element again)
class FileDirTree:
    """File(leaf) + dir(node) part of a Merkle tree. No hashes. May consist of
    multiple independent sub-graphs (e.g. if data is brought in by updata()),
    thus there is no single "top" element which could be used for recursive
    hash calculation. But we do explicit leaf hash calculation in parallel
    anyway in MerkleTree, so no need for recursive magic.
    """

    def __init__(self, dr=None, files=None):
        self.dr = dr
        self.files = files
        assert [files, dr].count(None) == 1, "dr or files must be None"
        self.build_tree()

    @staticmethod
    def walk_files(files):
        """Mimic os.walk() given a list of files.

        Example
        -------
        >>> for root,_,files in walk_files(files):
        ...     <here be code>

        Difference to os.walk(): The middle return arg is None and the order is
        not top-down.
        """
        dct = defaultdict(list)
        for fn in files:
            dct[os.path.dirname(fn)].append(os.path.basename(fn))
        for root, files in dct.items():
            yield root,None,files

    def walker(self):
        if self.files is not None:
            return self.walk_files(self.files)
        elif self.dr is not None:
            assert os.path.exists(self.dr) and os.path.isdir(self.dr)
            return os.walk(self.dr)
        else:
            raise Exception("files and dr are None")

    def build_tree(self):
        """Construct Merkle tree from all dirs and files in directory
        `self.dr`. Don't calculate fprs.
        """
        self.nodes = {}
        self.leafs = {}
        for root, _, files in self.walker():
            # make sure os.path.dirname() returns the parent dir
            if root.endswith('/'):
                root = root[:-1]
            node = Node(path=root, childs=[])
            for base in files:
                fn = os.path.join(root, base)
                co.debug_msg(f"build_tree: {fn}")
                # skip links
                if os.path.islink(fn):
                    co.debug_msg(f"skip link: {fn}")
                    continue
                assert os.path.isfile(fn)
                leaf = Leaf(path=fn)
                node.add_child(leaf)
                self.leafs[fn] = leaf
            # add node as child to parent node
            # root        = /foo/bar/baz
            # parent_root = /foo/bar
            self.nodes[root] = node
            parent_root = os.path.dirname(root)
            if parent_root in self.nodes.keys():
                self.nodes[parent_root].add_child(node)

    def update(self, other):
        for name in ['nodes', 'leafs']:
            attr = getattr(self, name)
            attr.update(getattr(other, name))


class MerkleTree:
    def __init__(self, tree, calc=True):
        self.nprocs = cfg.nprocs
        self.nthreads = cfg.nthreads
        self.tree = tree
        # Change only for benchmarks and debugging, should always be True in
        # production
        self.share_leafs = cfg.share_leafs

        if calc:
            self.calc_fprs()

    # pool.map(lambda kv: (k, v.fpr), ...) in calc_fprs() doesn't work,
    # error is "Can't pickle ... lambda ...", same with defining _worker()
    # inside calc_fprs(), need to def it in outer scope
    @staticmethod
    def _worker(kv):
        return kv[0], kv[1].fpr

    def _calc_leaf_fprs(self):
        """Trigger recursive fpr calculation."""
        useproc = False
        # leafs can be calculated in parallel since there are no dependencies
        if self.nthreads == 1 and self.nprocs == 1:
            # same as
            #   self.leaf_fprs = dict((k,v.fpr) for k,v in self.leafs.items())
            # just looks nicer :)
            getpool = SequentialPoolExecutor
        elif self.nthreads == 1:
            assert self.nprocs > 1
            getpool = lambda: ProcessPoolExecutor(self.nprocs)
            useproc = True
        elif self.nprocs == 1:
            assert self.nthreads > 1
            getpool = lambda: ThreadPoolExecutor(self.nthreads)
        else:
            getpool = lambda: ProcessAndThreadPoolExecutor(nprocs=self.nprocs,
                                                           nthreads=self.nthreads)
            useproc = True
        with getpool() as pool:
            self.leaf_fprs = dict(pool.map(self._worker,
                                           self.tree.leafs.items(),
                                           chunksize=1))

        # The node_fprs calculation below causes a slowdown with
        # ProcessPoolExecutor if we do not assign calculated leaf fprs
        # beforehand. This is b/c we do not operate on self.leaf_fprs, which
        # WAS calculated fast in parallel, but on MerkleTree. MerkleTree is NOT
        # shared between processes. multiprocessing spawns N new processes, ech
        # with it's own MerkleTree object, and each will calculate
        # approximately len(leafs)/N fprs, which are then collected in
        # leaf_fprs. Therefore, when we leave the pool context, the
        # MerkleTree objects of each sub-process are deleted, while the main
        # process MerkleTree object is still empty! Then, the node_fprs
        # calculation below triggers a new fpr calculation for the entire tree
        # of the main process all over again. We work around that by setting
        # leaf.fpr by hand. Since the main process' MerkleTree is empty, we
        # don't need to test if leaf.fpr is already populated (for that, we'd
        # need to extend the lazyprop decorator anyway).
        if useproc and self.share_leafs:
            for leaf in self.tree.leafs.values():
                leaf.fpr = self.leaf_fprs[leaf.path]

    def _calc_node_fprs(self):
        # v.fpr attribute access triggers recursive fpr calculation in all
        # leafs and nodes connected to this one. Since we do not assume the
        # exietence of a single top node, we iterate thru all nodes
        # explicitely. lazyprop makes sure we don't do anything twice.
        self.node_fprs = dict((k,v.fpr) for k,v in self.tree.nodes.items())

    def _calc_fprs(self):
        self._calc_leaf_fprs()
        self._calc_node_fprs()

    def set_leaf_fpr_func(self, limit):
        co.debug_msg(f"auto_limit: limit={co.size2str(limit)}")
        bs = adjust_blocksize(cfg.blocksize, limit)
        if limit is None:
            leaf_fpr_func = functools.partial(hash_file,
                                              blocksize=bs)
        else:
            leaf_fpr_func = functools.partial(hash_file_limit_core,
                                              blocksize=bs,
                                              limit=limit)

        for leaf in self.tree.leafs.values():
            leaf.fpr_func = leaf_fpr_func

    # leaf_fprs, node_fprs:
    #   {path1: fprA,
    #    path2: fprA,
    #    path3: fprB,
    #    path4: fprC,
    #    path5: fprD,
    #    path6: fprD,
    #    path7: fprD,
    #    ...}
    #
    # inverse_*_fprs:
    #    fprA: [path1, path2],
    #    fprB: [path3],
    #    fprC: [path4],
    #    fprD: [path5, path6, path7],
    #    ...}
    def inverse_leaf_fprs(self):
        return co.invert_dict(self.leaf_fprs)

    def inverse_node_fprs(self):
        return co.invert_dict(self.node_fprs)

    def _same_leafs_merged(self):
        """
        Returns
        -------
        set
            {path1, path2, path5, path6, path7}
        """
        inv = self.inverse_leaf_fprs()
        return set(itertools.chain(*(pp for pp in inv.values() if len(pp)>1)))

    def calc_fprs(self):
        max_limit = max(os.path.getsize(leaf.path) for leaf in
                        self.tree.leafs.values())
        if cfg.limit == 'auto':
            def itr(limit):
                yield limit
                while True:
                    limit = limit * cfg.auto_limit_increase_fac
                    if limit <= max_limit:
                        yield limit
                    else:
                        co.debug_msg("auto_limit: limit > max file size, stop")
                        break
            limit_itr = itr(cfg.auto_limit_min)
            self.set_leaf_fpr_func(next(limit_itr))
            self._calc_leaf_fprs()
            slm = self._same_leafs_merged()
            slm_old = slm
            # prevent early convergence
            slm_first = slm
            co.debug_msg(f"auto_limit: #same leafs = {len(slm)}")
            for limit in limit_itr:
                for path in slm:
                    del self.tree.leafs[path].fpr
                    co.debug_msg(f"auto_limit: del leaf fpr: {path}")
                self.set_leaf_fpr_func(limit)
                self._calc_leaf_fprs()
                slm = self._same_leafs_merged()
                co.debug_msg(f"auto_limit: #same leafs = {len(slm)}")
                if slm_old == slm and slm != slm_first:
                    break
                else:
                    slm_old = slm
            self._calc_node_fprs()
        else:
            self.set_leaf_fpr_func(cfg.limit)
            self._calc_fprs()

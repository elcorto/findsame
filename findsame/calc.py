"""
python3
-------

* Traversing dict.items() is truly random. We use dicts a lot and the code's
  output order is unpredictable. With python2, it was the same across repeated
  runs -- by accident (?) since dicts were always advertised as being
  random-order access structures.

  We get same-order output in different runs if we replace each {}/dict() with
  an OrderedDict(). Still, the output order is different from the
  python2-generated ref_output in test/.

* The code is slower. No bench yet, but it seems to be startup time, maybe
  imports?

* To make tests pass, we need to sort the output, as well as the ref_output
  generated with python2.
"""

import os, hashlib, sys
##from multiprocessing import Pool # same as ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from findsame import common as co
from findsame.config import config
from findsame.parallel import ProcessAndThreadPoolExecutor, \
    SequentialPoolExecutor

VERBOSE = False
HASHFUNC = hashlib.sha1


def hashsum(x):
    """SHA1 hash of a string."""
    return HASHFUNC(x.encode()).hexdigest()


def hash_file(fn, blocksize=config.blocksize):
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


def hash_file_limit(fn, blocksize=config.blocksize, limit=None):
    assert limit is not None
    _blocksize = limit if blocksize > limit else blocksize
    if _blocksize < limit:
        while limit % _blocksize != 0:
            _blocksize -= 1
        assert _blocksize > 0
    hasher = HASHFUNC()
    size = 0
    with open(fn, 'rb') as fd:
        buf = fd.read(_blocksize)
        size += len(buf)
        while buf and size <= limit:
            hasher.update(buf)
            buf = fd.read(_blocksize)
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
    def __init__(self, name='noname'):
        self.kind = None
        self.name = name

    def __repr__(self):
        return "{}:{}".format(self.kind, self.name)
    
    @co.lazyprop
    def fpr(self):
        if VERBOSE:
            co.debug_msg("fpr: {}".format(self.name))
        return self._get_fpr()

    def _get_fpr(self):
        raise NotImplementedError


class Node(Element):
    def __init__(self, *args, childs=None, **kwds):
        super(Node, self).__init__(*args, **kwds)
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
        # XXX really need that list here, what about genexpr?
        return self._merge_fpr([c.fpr for c in self.childs])


class Leaf(Element):
    def __init__(self, *args, fn=None, fpr_func=hash_file, **kwds):
        super(Leaf, self).__init__(*args, **kwds)
        self.kind = 'leaf'
        self.fn = fn
        self.fpr_func = fpr_func

    def _get_fpr(self):
        return self.fpr_func(self.fn)


class MerkleTree:
    def __init__(self, dr, calc=True, config=config, leaf_fpr_func=hash_file):
        self.nprocs = config.nprocs
        self.nthreads = config.nthreads
        self.dr = dr
        # only for benchmarks and debugging
        self.share_leafs = config.share_leafs
        self.leaf_fpr_func = leaf_fpr_func
        assert os.path.exists(self.dr) and os.path.isdir(self.dr)
        self.build_tree()
        if calc:
            self.calc_fprs()

    def build_tree(self):
        """Construct Merkle tree from all dirs and files in directory
        `self.dr`. Don't calculate fprs.
        """
        nodes = {}
        leafs = {}
        top = None
        for root, dirs, files in os.walk(self.dr):
            # make sure os.path.dirname() returns the parent dir
            if root.endswith('/'):
                root = root[:-1]
            node = Node(name=root, childs=[])
            for base in files:
                fn = os.path.join(root, base)
                if VERBOSE:
                    co.debug_msg("build_tree: {}".format(fn))
                # skipping links
                if os.path.exists(fn) and os.path.isfile(fn) \
                        and not os.path.islink(fn):
                    leaf = Leaf(name=fn, fn=fn, fpr_func=self.leaf_fpr_func)
                    node.add_child(leaf)
                    leafs[fn] = leaf
                else:
                    co.debug_msg("SKIP: {}".format(fn))
            # add node as child to parent node, relies on top-down os.walk
            # root        = /foo/bar/baz
            # parent_root = /foo/bar
            nodes[root] = node
            parent_root = os.path.dirname(root)
            # XXX should always be true, eh??
            if parent_root in nodes.keys():
                nodes[parent_root].add_child(node)
            if top is None:
                top = node
            self.top = top
            self.nodes = nodes
            self.leafs = leafs
    
    # pool.map(lambda kv: (k, v.fpr), ...) in calc_fprs() doesn't work,
    # error is "Can't pickle ... lambda ...", same with defining _worker()
    # inside calc_fprs(), need to def it in outer scope
    @staticmethod
    def _worker(kv):
        return kv[0], kv[1].fpr
    
    # XXX maybe add special-case code to ProcessAndThreadPoolExecutor
    def calc_fprs(self):
        useproc = False
        """Trigger recursive fpr calculation."""
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
                                           self.leafs.items(),
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
            for leaf in self.leafs.values():
                leaf.fpr = self.leaf_fprs[leaf.name]
        
        # v.fpr attribute access triggers recursive fpr calculation for all
        # nodes. For only kicking off the calculation, it would be sufficient
        # to call top.fpr . However, we also put all node fprs in a dict here,
        # so this is implicit.
        self.node_fprs = dict((k,v.fpr) for k,v in self.nodes.items())

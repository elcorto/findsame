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


def hashsum(x, encoding='utf-8'):
    """Hash of a string. Uses HASHFUNC."""
    return HASHFUNC(x.encode(encoding=encoding)).hexdigest()


# Hash of an empty file as returned by hash_file(): file content is '' but the
# file size is 0 (an int) and the hash of '0' has another value than
# hashsum(''). Encoding doesn't matter for '0' since ascii is a subset of all
# of them up to code point 127.
#
# We have:
#
# empty file
#   * filesize = 0,
#   * fpr=hashsum('0') -- result of hash_file(Leaf('/path/to/empty_file'))
# empty dir
#   * zero files
#   * fpr=hashsum('') -- definition
# dirs with N empty files:
#   * fpr = hashsum(N times hashsum('0'))
#   * so all dirs with the same number of empty files will have the same hash
EMPTY_FILE_FPR = hashsum('0')
EMPTY_DIR_FPR = hashsum('')


def hash_file(leaf, blocksize=None, use_filesize=True):
    """Hash file content, using filesize as additional info.

    Parameters
    ----------
    leaf : Leaf
    blocksize : int, None
        size of block (bytes) to read at once; None = read whole file
    use_filesize : bool

    Notes
    -----
    Using `blocksize` stolen from:
    http://pythoncentral.io/hashing-files-with-python/ . Result is the same as
    e.g. ``sha1sum <filename>`` when use_filesize=False (or as a hack we set
    leaf.filesize = '' (zero length byte string)).
    """
    hasher = HASHFUNC()
    if use_filesize:
        hasher.update(str(leaf.filesize).encode('ascii'))
    with open(leaf.path, 'rb') as fd:
        buf = fd.read(blocksize)
        while buf:
            hasher.update(buf)
            buf = fd.read(blocksize)
    return hasher.hexdigest()


def hash_file_limit(leaf, blocksize=None, limit=None, use_filesize=True):
    """Same as :func:`hash_file`, but read only exactly `limit` bytes."""
    # We have the same code (adjust blocksize, assert modulo) in the main
    # script as early exit check, but this function may also be used elsewhere
    # (benckmark, tests) w/o being called in MerkleTree where the already
    # correct values cfg.blocksize and cfg.limit are used to call us here, so
    # we need this. Timing shows that all asserts here cost virtually nothing.
    assert blocksize is not None and (blocksize > 0), f"blocksize={blocksize}"
    assert (limit is not None) and (limit > 0), f"limit={limit}"
    bs = blocksize if blocksize < limit else limit
    assert limit % bs == 0, f"limit={co.size2str(limit)} % bs={co.size2str(bs)} != 0"
    hasher = HASHFUNC()
    if use_filesize:
        hasher.update(str(leaf.filesize).encode('ascii'))
    with open(leaf.path, 'rb') as fd:
        while True:
            pos = fd.tell()
            if pos == leaf.filesize or pos == limit:
                break
            hasher.update(fd.read(bs))
    return hasher.hexdigest()


def split_path(path):
    """//foo/bar/baz -> ['foo', 'bar', 'baz']"""
    return [x for x in path.split('/') if x != '']


class Element:
    def __init__(self, path=None):
        self.kind = None
        self.path = path

    def __repr__(self):
        return f"{self.kind}:{self.path}"

    @co.lazyprop
    def fpr(self):
        fpr = self._get_fpr()
        co.debug_msg(f"fpr: {self.kind}={self.path} fpr={fpr}")
        return fpr

    def _get_fpr(self):
        raise NotImplementedError


class Node(Element):
    def __init__(self, *args, childs=None, **kwds):
        super().__init__(*args, **kwds)
        self.kind = 'node'
        self.childs = childs

    def add_child(self, child):
        self.childs.append(child)

    # The clean hashlib style way is smth like
    #   hasher = HASHFUNC()
    #   for fpr in sorted(fpr_lst):
    #       hasher.update(fpr.encode())
    #   ... etc ...
    # instead of taking the hash of a concatenated string. Not that the
    # resulting hash would chnage, it's just better style.
    @staticmethod
    def _merge_fpr(fpr_lst):
        """Hash of a list of fpr strings. Sort them first to ensure reproducible
        results."""
        nn = len(fpr_lst)
        if nn > 1:
            return hashsum(''.join(sorted(fpr_lst)))
        elif nn == 1:
            return hashsum(fpr_lst[0])
        # no childs, this happen if
        # * we really have a node (=dir) w/o childs
        # * we have only links in the dir .. we currently treat
        #   that dir as empty since we ignore links
        else:
            return EMPTY_DIR_FPR

    def _get_fpr(self):
        return self._merge_fpr([c.fpr for c in self.childs])


class Leaf(Element):
    def __init__(self, *args, fpr_func=hash_file, **kwds):
        super().__init__(*args, **kwds)
        self.kind = 'leaf'
        self.fpr_func = fpr_func
        self.filesize = os.path.getsize(self.path)

    def _get_fpr(self):
        return self.fpr_func(self)


class FileDirTree:
    """File (leaf) + dir (node) part of a Merkle tree. No hash calculation
    here.

    May consist of multiple independent sub-graphs (e.g. if data is brought in
    by update()), thus there is no single "top" element which could be used for
    recursive hash calculation (more details in MerkleTree).

    Notes
    -----
    Merkle tree (single graph) with one top node:

    ::

        $ tree test
        test                      # top node
        └── a                     # node
            ├── b                 # node
            │   ├── c             # node
            │   │   └── file1     # leaf
            │   ├── file4         # leaf
            │   └── file5         # leaf
            ├── d                 # node
            │   └── e             # node
            │       └── file2     # leaf
            └── file3             # leaf

        >>> [(r,d,f) for r,d,f in os.walk('test/')]
        [('test/', ['a'], []),
         ('test/a', ['b', 'd'], ['file3']),
         ('test/a/b', ['c'], ['file5', 'file4']),
         ('test/a/b/c', [], ['file1']),
         ('test/a/d', ['e'], []),
         ('test/a/d/e', [], ['file2'])]
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
            _dn = os.path.dirname(fn)
            dct[os.path.curdir if _dn == '' else _dn].append(os.path.basename(fn))
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
                assert os.path.isfile(fn), fn
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
    """
    In the simplest setting, the tree is a single graph with a top node. In
    that case, a naive serial calculation would just call top.fpr, which would
    trigger recursive hash (fpr) calculations for all nodes and their connected
    leafs, thus populating each tree element (leaf, node) with a fpr value.

    Here, we have two differences.

    (1) We deal with possibly multiple distinct sub-graphs, thus there is no
    single top element. It was a design decision to NOT model this using
    multiple MerkleTree instances (sub-graphs) with a top node each, for
    reasons which will become clear below. For one, we don't need to perform
    complicated graph calculations to separate nodes and leafs into separate
    graphs.

    (2) We calculate leaf fprs in parallel explicitly before node fprs, thus
    leaf fprs are never calculated by recursive node fprs. Therefore, we do not
    need a top node. Calculating leafs in parallel is easy since they are
    independent from one another.

    These two points imply to issues, which are however easily solved:

    _calc_node_fprs(): self.node_fprs
    ---------------------------------
    node.fpr attribute access triggers recursive fpr calculation in all leafs
    and nodes connected to this node. But since we do not assume the existence
    of a single top node, we need to iterate thru all nodes explicitly. The
    @lazyprop decorator of the fpr attribute (see class Element) makes sure we
    don't calculate anything more than once. Profiling shows that the decorator
    doesn't consume much resources, compared to hash calculation itself.

    _calc_leaf_fprs(): share_leafs
    ------------------------------
    Note: This applies ONLY to ProcessPoolExecutor, i.e. multiprocessing, which
    NOT the fastest parallelization method here (ThreadPoolExecutor, i.e.
    multithreading is better).

    The calculation of self.node_fprs in _calc_node_fprs() causes a slowdown
    with ProcessPoolExecutor if we do not assign calculated leaf fprs
    beforehand. This is b/c when calculating node_fprs, we do not operate on
    self.leaf_fprs, which WAS calculated fast in parallel, but on self.tree (a
    FileDirTree instance). This is NOT shared between processes.
    multiprocessing spawns N new processes, each with its own MerkleTree
    object, and each will calculate approximately len(leafs)/N fprs, which are
    then collected in leaf_fprs. Therefore, when we leave the pool context, the
    MerkleTree objects (i.e. self) of each sub-process are deleted, while the
    main process' self.tree object is still empty (no element has an fpr
    attribute value)! Then, the node_fprs calculation in _calc_node_fprs()
    triggers a new fpr calculation for the entire tree of the main process all
    over again. We work around that by setting leaf.fpr by hand. Since the main
    process' self.tree is empty, we don't need to test if leaf.fpr is already
    populated (for that, we'd need to extend the @lazyprop decorator anyway).

    some attributes
    ---------------
    leaf_fprs, node_fprs:
      {path1: fprA,
       path2: fprA,
       path3: fprB,
       path4: fprC,
       path5: fprD,
       path6: fprD,
       path7: fprD,
       ...}

    invert_dict(leaf_fprs), invert_dict(node_fprs):
       fprA: [path1, path2],
       fprB: [path3],
       fprC: [path4],
       fprD: [path5, path6, path7],
       ...}
    """
    def __init__(self, tree):
        """
        Parameters
        ----------
        tree : FileDirTree instance
        """
        self.tree = tree
        self.set_leaf_fpr_func(cfg.limit)
        self.calc_leaf_fprs()
        self.calc_node_fprs()

    def set_leaf_fpr_func(self, limit):
        if limit is None:
            leaf_fpr_func = functools.partial(hash_file,
                                              blocksize=cfg.blocksize)
        else:
            leaf_fpr_func = functools.partial(hash_file_limit,
                                              blocksize=cfg.blocksize,
                                              limit=limit,
                                              use_filesize=True)

        for leaf in self.tree.leafs.values():
            leaf.fpr_func = leaf_fpr_func

    # pool.map(lambda kv: (k, v.fpr), ...) in _calc_leaf_fprs() doesn't work,
    # error is "Can't pickle ... lambda ...", same with defining _fpr_worker()
    # inside _calc_leaf_fprs(), need to def it in outer scope
    @staticmethod
    def fpr_worker(leaf):
        return leaf.path, leaf.fpr

    def calc_leaf_fprs(self):
        # whether we use multiprocessing
        useproc = False

        if cfg.nthreads == 1 and cfg.nprocs == 1:
            # same as
            #   self.leaf_fprs = dict((k,v.fpr) for k,v in self.tree.leafs.items())
            # just looks nicer :)
            getpool = SequentialPoolExecutor
        elif cfg.nthreads == 1:
            assert cfg.nprocs > 1
            getpool = lambda: ProcessPoolExecutor(cfg.nprocs)
            useproc = True
        elif cfg.nprocs == 1:
            assert cfg.nthreads > 1
            getpool = lambda: ThreadPoolExecutor(cfg.nthreads)
        else:
            getpool = lambda: ProcessAndThreadPoolExecutor(nprocs=cfg.nprocs,
                                                           nthreads=cfg.nthreads)
            useproc = True

        with getpool() as pool:
            self.leaf_fprs = dict(pool.map(self.fpr_worker,
                                           self.tree.leafs.values(),
                                           chunksize=1))

        if useproc and cfg.share_leafs:
            for leaf in self.tree.leafs.values():
                leaf.fpr = self.leaf_fprs[leaf.path]

    def calc_node_fprs(self):
        self.node_fprs = dict((node.path,node.fpr) for node in self.tree.nodes.values())

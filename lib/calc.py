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
from findsame.lib import common as co

VERBOSE = False
BLOCKSIZE = 256*1024

def debug_msg(msg):
    sys.stderr.write(msg + "\n")


def hashsum(x):
    """SHA1 hash of a string."""
    return hashlib.sha1(x.encode()).hexdigest()


def hash_file(fn, blocksize=BLOCKSIZE):
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
    hasher = hashlib.sha1()
    with open(fn, 'rb') as fd:
        buf = fd.read(blocksize)
        while buf:
            hasher.update(buf)
            buf = fd.read(blocksize)
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
        self.name = name

    def __repr__(self):
        return "{}:{}".format(self.kind, self.name)
    
    @co.lazyprop
    def hash(self):
        if VERBOSE:
            debug_msg("hash: {}".format(self.name))
        return self._get_hash()

    def _get_hash(self):
        raise NotImplementedError


class Node(Element):
    def __init__(self, *args, childs=None, **kwds):
        super(Node, self).__init__(*args, **kwds)
        self.childs = childs

    def add_child(self, child):
        self.childs.append(child)

    @staticmethod
    def _merge_hash(hash_lst):
        """Hash of a list of hash strings. Sort them first to ensure reproducible
        results."""
        nn = len(hash_lst)
        if nn > 1:
            return hashsum(''.join(sorted(hash_lst)))
        elif nn == 1:
            return hash_lst[0]
        # no childs, this happen if
        # * we really have a node (=dir) w/o childs
        # * we have only links in the dir .. we currently treat
        #   that dir as empty since we ignore links
        else:
            return hashsum('')

    def _get_hash(self):
        return self._merge_hash([c.hash for c in self.childs])


class Leaf(Element):
    def __init__(self, *args, fn=None, blocksize=BLOCKSIZE, **kwds):
        super(Leaf, self).__init__(*args, **kwds)
        self.fn = fn
        self.blocksize = blocksize

    def _get_hash(self):
        return hash_file(self.fn, blocksize=self.blocksize)


class MerkleTree:
    def __init__(self, dr, calc=True, nworkers=None, parallel='threads',
                 blocksize=BLOCKSIZE):
        self.nworkers = nworkers
        self.blocksize = blocksize
        self.dr = dr
        pool_class_map = {'threads': ThreadPoolExecutor,
                          'procs': ProcessPoolExecutor}
        self.pool_class = pool_class_map.get(parallel, None)
        if self.pool_class is None:
            raise Exception("parallel must be one "
                            "of {}, was: {}".format(pool_class_map.keys(),
                                                    parallel))
        assert os.path.exists(self.dr) and os.path.isdir(self.dr)
        self.build_tree()
        if calc:
            self.calc_hashes()

    def build_tree(self):
        """Construct Merkle tree from all dirs and files in directory
        `self.dr`. Don't calculate hashes.
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
                    debug_msg("build_tree: {}".format(fn))
                # skipping links
                if os.path.exists(fn) and os.path.isfile(fn):
                    leaf = Leaf(name=fn, fn=fn, blocksize=self.blocksize)
                    node.add_child(leaf)
                    leafs[fn] = leaf
                else:
                    debug_msg("SKIP: {}".format(fn))
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
    
    # pool.map(lambda kv: (k, v.hash), ...) in calc_hashes() doesn't work,
    # error is "Can't pickle ... lambda ...", same with defining _worker()
    # inside calc_hashes(), need to def it in outer scope
    @staticmethod
    def _worker(kv):
        return kv[0], kv[1].hash

    def calc_hashes(self):
        """Trigger recursive hash calculation."""
        # leafs can be calculated in parallel since there are no dependencies,
        # but the whole operation is about 50% IO-bound, speedup is moderate or
        # even < 1
        if (self.nworkers is not None) and (self.nworkers > 1):
            with self.pool_class(self.nworkers) as pool:
                self.file_hashes = dict(pool.map(self._worker, self.leafs.items()))
        else:
            self.file_hashes = dict((k,v.hash) for k,v in self.leafs.items())
        self.dir_hashes = dict((k,v.hash) for k,v in self.nodes.items())


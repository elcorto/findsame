#!/usr/bin/python3

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

import os, hashlib, argparse, json, functools, sys
from multiprocessing import Pool


class lazyprop(object):
    """Decorator for creating lazy evaluated properties.
    The property should represent non-mutable data, as it replaces itself.
    
    kudos: Cyclone over at stackoverflow!
    http://stackoverflow.com/questions/3012421/python-lazy-property-decorator
    """
    def __init__(self,fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self,obj,cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj,self.func_name,value)
        return value


def debug_msg(msg):
    sys.stderr.write(msg + "\n")


def hashsum(x):
    """SHA1 hash of a string."""
    return hashlib.sha1(x.encode()).hexdigest()


def hash_file(fn, blocksize=1024**2):
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
        self.kind = None

    def __repr__(self):
        return "{}:{}".format(self.kind, self.name)
    
    @lazyprop
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
        self.kind = 'node'

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
    def __init__(self, *args, fn=None, **kwds):
        super(Leaf, self).__init__(*args, **kwds)
        self.fn = fn
        self.kind = 'leaf'

    def _get_hash(self):
        return hash_file(self.fn)


class MerkleTree:
    def __init__(self, dr, calc=True, ncores=None):
        self.ncores = ncores
        self.dr = dr
        assert os.path.exists(self.dr) and os.path.isdir(self.dr)
        self.build_tree()
        if calc:
            self.calc_hashes()

    def build_tree(self):
        """Construct Merkle tree from all dirs and files in directory `dr`. Don't
        calculate hashes.
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
                    leaf = Leaf(name=fn, fn=fn)
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
        if self.ncores:
            with Pool(self.ncores) as pool:
                self.file_hashes = dict(pool.map(self._worker, self.leafs.items()))
        else:
            self.file_hashes = dict((k,v.hash) for k,v in self.leafs.items())
        self.dir_hashes = dict((k,v.hash) for k,v in self.nodes.items())


def find_same(hashes):
    """Given a dict with names and hashes, "invert" the dict to find all names
    which have the same hash.

    Parameters
    ----------
    hashes: dict
        {name1: hashA,
         name2: hashA,
         name3: hashB,
         ...}

    Returns
    -------
    dict
        {hashA: [name1, name2],
         hashB: [name3],
         ...}
    """
    store = dict()
    for name,hsh in hashes.items():
        if hsh in store.keys():
            store[hsh].append(name)
        else:
            store[hsh] = [name]
    # sort to force reproducible results
    return dict((k,sorted(v)) for k,v in store.items())


if __name__ == '__main__':

    desc = "Find same files and dirs based on file hashes."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('files_dirs', nargs='+', metavar='file/dir',
                        help='files and/or dirs to compare', default=[])
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False,
                        help='verbose')
    parser.add_argument('-n', '--ncores', type=int,
                        default=None,
                        help='number of processes for parallel hash calc '
                             'in Merkle tree')
    args = parser.parse_args()

    VERBOSE = args.verbose

    file_hashes = dict()
    dir_hashes = dict()
    for name in args.files_dirs:
        # skipping links
        if os.path.isfile(name):
            file_hashes[name] = hash_file(name)
        elif os.path.isdir(name):
            tree = MerkleTree(name, calc=True, ncores=args.ncores)
            file_hashes.update(tree.file_hashes)
            dir_hashes.update(tree.dir_hashes)
        else:
            debug_msg("SKIP: {}".format(name))

    file_store = find_same(file_hashes)
    dir_store = find_same(dir_hashes)

    # result:
    #     {hashA: {typX: [name1, name2],
    #              typY: [name3]},
    #      hashB: {typX: [...]},
    #      ...}
    result = dict()
    empty = hashsum('')
    for kind, dct in [('dir', dir_store), ('file', file_store)]:
        for hsh, names in dct.items():
            hsh_dct = result.get(hsh, {})
            if len(names) > 1:
                # exclude single deep files, where each upper dir has the same
                # hash as the deep file
                #   foo/
                #   foo/bar/
                #   foo/bar/baz
                #   foo/bar/baz/file
                # In that case for kind=='dir':
                #   names = ['foo', 'foo/bar', 'foo/bar/baz']
                #   lens  = [1,2,3]
                #   diffs = [1,1,1]
                if kind == 'dir':
                    lens = [len(split_path(x)) for x in names] 
                    diffs = map(lambda x,y: y-x, lens[:-1], lens[1:])
                    if functools.reduce(lambda x,y: x == y == 1, diffs):
                        continue
                if hsh == empty:
                    typ = '{}:empty'.format(kind)
                else:
                    typ = '{}'.format(kind)
                typ_names = hsh_dct.get(typ, []) + names
                hsh_dct.update({typ: typ_names})
                result.update({hsh: hsh_dct})
    print(json.dumps(result))

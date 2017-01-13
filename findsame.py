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

import os, hashlib, sys, argparse, subprocess
import numpy as np


def hashsum(x):
    return hashlib.sha1(x.encode()).hexdigest()


def hash_file(fn, blocksize=1024**2):
    """
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


def sort_hash_lst(seq):
    return np.sort(list(seq)).tolist()


def split_path(path):
    return [x for x in path.split('/') if x != '']


def _dict(*args, **kwds):
    return dict(*args, **kwds)

# In [38]: !tree test
# test
# └── a
#     ├── b
#     │   ├── c
#     │   │   └── file1
#     │   ├── file4
#     │   └── file5
#     ├── d
#     │   └── e
#     │       └── file2
#     └── file3
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
# 
def get_hashes(dr):
    """Hash each file in directory `dr` recursively.
    
    Parameters
    ----------
    dr : str

    Returns
    -------
    file_hashes : dict
        keys = file names (full path starting with `dr`)
        vals = hash string
    """
    file_hashes = _dict()
    dir_hashes = _dict()
    for root, dirs, files in os.walk(dr):
        dir_hashes[root] = []
        for base in files:
            fn = os.path.join(root, base)
            # sanity check, i.e. strange dangling symlinks
            if os.path.exists(fn) and os.path.isfile(fn):
                hsh = hash_file(fn)
                file_hashes[fn] = hsh
                for dr in dir_hashes.keys():
                    if is_subpath(fn, dr):
                        dir_hashes[dr].append(hsh)
            else:    
                print("ERR: {}".format(fn))
    for dr,lst in dir_hashes.items():
        # sort to make sure the hash is invariant w.r.t. the order of file
        # names
        dir_hashes[dr] = hashsum(''.join(sort_hash_lst(lst)))
    return file_hashes, dir_hashes


def is_subpath(sub, top):
    return len(sub) > len(top) and sub.startswith(top)


def find_same(hashes):
    store = _dict()
    for name,hsh in hashes.items():
        if hsh in store.keys():
            store[hsh].append(name)
        else:     
            store[hsh] = [name]
    # sort to force reproducible results        
    return _dict((k,sort_hash_lst(v)) for k,v in store.items())


if __name__ == '__main__':

    desc = "Find same files and dirs based on file hashes."
    parser = argparse.ArgumentParser(description=desc) 
    parser.add_argument('file/dir', nargs='+',
                        help='files and/or dirs to compare')
    args = parser.parse_args()
    
    file_hashes = _dict()
    dir_hashes = _dict()  
    for name in vars(args)['file/dir']:
        if os.path.isfile(name):
            file_hashes[name] = hash_file(name)
        elif os.path.isdir(name):
            this_file_hashes, this_dir_hashes = get_hashes(name)
            file_hashes.update(this_file_hashes)
            dir_hashes.update(this_dir_hashes)
        else:
            print("SKIP: {}".format(name)) 
    
    file_store = find_same(file_hashes)
    dir_store = find_same(dir_hashes)
    
    empty = hashsum('')
    for typ, dct in [('dir', dir_store), ('file', file_store)]:
        for hsh,names in dct.items():
            if len(names) > 1:
                # exclude single deep files, where each upper dir has the same
                # hash as the deep file
                #   foo/
                #   foo/bar/
                #   foo/bar/baz
                #   foo/bar/baz/file
                # In that case, names = ['foo', 'foo/bar', 'foo/bar/baz'] for
                # typ=='dir'.
                if typ == 'dir':
                    tmp = np.array([len(split_path(x)) for x in names],
                                   dtype=int)
                    if (np.diff(tmp) == np.ones((len(tmp)-1,),
                                                dtype=int)).all():
                        continue
                if hsh == empty:
                    prfx = '{}:empty: '.format(typ)
                else:     
                    prfx = '{}: '.format(typ)
                for name in names:
                    print("{prfx}{name}".format(prfx=prfx, name=name))
                print("")

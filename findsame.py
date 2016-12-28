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


def sort_hash_lst(str_lst):
    return np.sort(str_lst).tolist()


def split_path(path):
    return [x for x in path.split('/') if x != '']


def _dict(*args, **kwds):
    return dict(*args, **kwds)


def get_file_hashes(dr):
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
    for root, dirs, files in os.walk(dr):
        for base in files:
            fn = os.path.join(root, base)
            # sanity check, i.e. strange dangling symlinks
            if os.path.exists(fn) and os.path.isfile(fn):
                file_hashes[fn] = hash_file(fn)
            else:    
                print("ERR {}".format(fn))
    return file_hashes


def get_dir_lst(dr):
    return [root for root, dirs, files in os.walk(dr)]


def is_subpath(sub, top):
    """Whether `sub` is a subdir of dirname `top` (in case `sub` is a dir) or
    if the file pointed to by `sub` is below `top` (arbitrary levels deep). 
    
    Examples
    --------
    >>> is_subpath('a/b', 'a')
    True
    >>> is_subpath('a', 'a/b')
    False
    >>> is_subpath('a', 'a')
    False
    """
    ts = split_path(top)
    ss = split_path(sub)
    lts = len(ts)
    lss = len(ss)
    if lts < lss:
        return ts == ss[:lts]
    else:
        return False


def get_dir_hashes(file_hashes, dir_lst=None):
    """Hash of dirs derived from file names in `file_hashes` or dirs in
    `dir_lst`. Dir hash is built from the hashes of all files it containes
    """
    if dir_lst is None:
        dir_lst = set(os.path.dirname(x) for x in file_hashes.keys())
    dir_hashes = _dict()
    for dr in dir_lst:
        dir_hashes[dr] = []
        for name,hsh in file_hashes.items():
            if is_subpath(name, dr):
                dir_hashes[dr] += [hsh]
    for dr,lst in dir_hashes.items():
        # sort to make sure the hash is invariant w.r.t. the order of file
        # names
        dir_hashes[dr] = hashsum(''.join(sort_hash_lst(lst)))
    return dir_hashes


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
    parser.add_argument('dir', nargs='+',
                        help='dirs to compare')
    args = parser.parse_args()
 
    file_hashes = _dict()
    dir_hashes = _dict()  
    for dr in vars(args)['dir']:
        this_file_hashes = get_file_hashes(dr)
        # pass dir_lst to catch also empty dirs w/o any files in it; the
        # dir_lst generated from file_hashes inside get_dir_hashes() contains
        # only dirs with files
        this_dir_hashes = get_dir_hashes(this_file_hashes,
                                         dir_lst=get_dir_lst(dr))
        file_hashes.update(this_file_hashes)
        dir_hashes.update(this_dir_hashes)
    
    file_store = find_same(file_hashes)
    dir_store = find_same(dir_hashes)
    
    empty = hashsum('')
    for typ, dct in [('dir', dir_store), ('file', file_store)]:
        for hsh,names in dct.items():
            if len(names) > 1:
                # exclude trivial case: dir contains only one subdir, no extra
                # files:
                #   foo/
                #   foo/bar/
                #   foo/bar/file
                # then the hash of foo/ and foo/bar/ are the same, don't need
                # to show that  
                if typ == 'dir' and len(names) == 2 and \
                   abs(len(split_path(names[0])) - len(split_path(names[1]))) == 1:
                    continue
                else:    
                    if hsh == empty:
                        prfx = '{}:empty: '.format(typ)
                    else:     
                        prfx = '{}: '.format(typ)
                    for name in names:
                        print("{prfx}{name}".format(prfx=prfx, name=name))
                    print("")

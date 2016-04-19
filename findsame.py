#!/usr/bin/env python

import os, hashlib
import numpy as np

def hashsum(x):
    return hashlib.sha1(x).hexdigest()


def hash_file(fn):
    with open(fn) as fd:
        return hashsum(fd.read())


def get_file_hashes(dr):
    """Hash each file in directory `dr` recursively.
    
    Returns
    -------
    file_hashes : dict
        keys = file names (full path starting with `dr`)
        vals = hash string
    """
    file_hashes = {}
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
    ts = [x for x in top.split('/') if x != '']
    ss = [x for x in sub.split('/') if x != '']
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
    dir_hashes = {}
    for dr in dir_lst:
        dir_hashes[dr] = []
        for name,hsh in file_hashes.iteritems():
            if is_subpath(name, dr):
                dir_hashes[dr] += [hsh]
    for dr,lst in dir_hashes.iteritems():
        # sort to make sure the hash is invariant w.r.t. the order of file
        # names
        dir_hashes[dr] = hashsum(''.join(np.sort(lst)))
    return dir_hashes


def find_same(hashes):
    store = {}
    for name,hsh in hashes.iteritems():
        if store.has_key(hsh):
            store[hsh].append(name)
        else:     
            store[hsh] = [name]
    return store


if __name__ == '__main__':

    import sys
    
    file_hashes = {}
    dir_hashes = {}
    for dr in sys.argv[1:]:
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
        for hsh,names in dct.iteritems():
            if len(names) > 1:
                if hsh == empty:
                    prfx = '{}:empty: '.format(typ)
                else:     
                    prfx = '{}: '.format(typ)
                for name in names:
                    print("{prfx}{name}".format(prfx=prfx, name=name))
                print("")

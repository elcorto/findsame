#!/usr/bin/python3

from io import IOBase
from itertools import product
import timeit, sys, os, copy
import pandas as pd
import numpy as np

pj = os.path.join

#------------------------------------------------------------------------------
# constants
#------------------------------------------------------------------------------

kiB = 1024
MiB = kiB**2
GiB = kiB**3


#------------------------------------------------------------------------------
# general helpers
#------------------------------------------------------------------------------

def seq2dicts(name, seq):
    """
    >>> seq2dicts('a', [1,2,3])
    [{'a': 1}, {'a': 2}, {'a': 3}]
    """
    return [{name: entry} for entry in seq]


# stolen from pwtools and adapted for python3
def is_seq(seq):
    if isinstance(seq, str) or \
       isinstance(seq, IOBase) or \
       isinstance(seq, dict):
       return False
    else:
        try:
            x=iter(seq)
            return True
        except:
            return False


def flatten(seq):
    for item in seq:
        if not is_seq(item):
            yield item
        else:
            for subitem in flatten(item):
                yield subitem


def merge_dicts(lst):
    dct = {}
    for entry in lst:
        dct.update(entry)
    return dct


def params2df(params):
    df = pd.DataFrame()
    for idx,dct in enumerate(params):
        df = df.append(pd.DataFrame(dct, index=[idx]))
    return df


def mkparams(*args):
    return [merge_dicts(flatten(entry)) for entry in product(*args)]


def run(df, func, params):
    for idx,dct in enumerate(params):
        row = copy.deepcopy(dct)
        row.update(func(dct))
        df_row = pd.DataFrame(row, index=[idx])
        df = df.append(df_row)
        print(df_row)
    return df


#------------------------------------------------------------------------------
# helpers for this study
#------------------------------------------------------------------------------

def size2str(filesize, sep=''):
    """Convert size in bytes to string with unit."""
    div = [(GiB, 'G'), (MiB, 'M'), (kiB, 'k'), (1, 'B')]
    for divsize, symbol in div:
        if filesize // divsize == 0:
            continue
        else:
            return "{:.1f}{}{}".format(filesize/divsize, sep, symbol)


def bytes_logspace(start, stop, num):
    return np.unique(np.logspace(np.log10(start),
                                 np.log10(stop),
                                 num).astype(int))


def bytes_linspace(start, stop, num):
    return np.unique(np.linspace(start,
                                 stop,
                                 num).astype(int))


def write(tmpdir, filesize_lst, collection_size):
    assert filesize_lst.max() <= collection_size
    print("writing data")
    filesize_dr_lst = []
    for filesize in filesize_lst:
        filesize_str = size2str(filesize)
        print("filesize: {}".format(filesize_str))
        dr = pj(tmpdir, 'filesize_{}'.format(filesize_str))
        filesize_dr_lst.append(dr)
        if not os.path.exists(dr):
            os.makedirs(dr)
            nfiles = collection_size // filesize
            data = b'x'*filesize
            for idx in range(nfiles):
                fn = pj(dr, 'file_{}'.format(idx))
                with open(fn, 'wb') as fd:
                    fd.write(data)
        else:
            print('already there: {}'.format(dr))
    return filesize_dr_lst


def func(dct, stmt=None, setup=None):
    timing = timeit.repeat(stmt.format(**dct),
                           setup,
                           repeat=3,
                           number=1)
    return {'timing': min(timing)}


def params_filter(params):
    return [p for p in params if p['blocksize'] <= p['filesize']] 


if __name__ == '__main__':
    tmpdir = sys.argv[1]

    setup = "from findsame import findsame as fs"
    stmt = "fs.main({files_dirs}, ncores={ncores}, blocksize={blocksize})"

    df = pd.DataFrame()
    collection_size = 100*MiB
    params = []
    
    # test individual file sizes
    cases = [(bytes_linspace(512*kiB, collection_size, 3),
              bytes_logspace(10*kiB, collection_size, 10),
              'blocksize'),
             (bytes_linspace(512*kiB, collection_size, 10),
              [64*kiB, 512*kiB],
              'filesize')] 

    for filesize, blocksize, study in cases:
        filesize_dr = write(tmpdir, filesize, collection_size)
        this = mkparams(zip(seq2dicts('filesize', filesize),
                            seq2dicts('filesize_dr', filesize_dr),
                            seq2dicts('filesize_str', list(map(size2str, filesize))),
                            seq2dicts('files_dirs', [[x] for x in filesize_dr])),
                        seq2dicts('study', [study]),
                        seq2dicts('ncores', [1]),
                        zip(seq2dicts('blocksize', blocksize),
                            seq2dicts('blocksize_str', list(map(size2str,
                                                                blocksize)))))
        params += this
        
##    params = params_filter(params)
    
    # collection of different file sizes
    filesize = bytes_linspace(512*kiB, collection_size, 5)
    blocksize = [512*kiB]
    testdir = pj(tmpdir, 'collection')
    filesize_dr = write(testdir, filesize, collection_size)
    
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', ['collection']),
                    seq2dicts('ncores', [1,2,4]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                        blocksize)))))
    params += this
    
    df = run(df, lambda p: func(p, stmt, setup), params)
    print(df)
    with open(pj(tmpdir, 'results.json'), 'w') as fd:
        fd.write(df.to_json())

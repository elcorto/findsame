#!/usr/bin/python3

"""
basic data struct for param study:

params = [{'foo': 1, 'bar': 'lala', ...},  # parameter set 1
          {'foo': 2, 'bar': 'zzz', ...},   # parameter set 2
          ...                              # ...
         ]

These are the basis of a pandas DataFrame (much like an SQL table, 2D array
w/ named columns and in case of DataFrame also variable data types) with
columns 'foo' and 'bar'. Benchmark results (column 'timing') are appended in
each run.

Below we have some helper functions which assist in creating `params`.
Basically, we define the to-be-varied parameters as "named sequences" (i.e.
list of dicts) and use itertools.product to loop over them.

    >>> from findsame.benchmark import benchmark as bm
    >>> import itertools
    >>> x=bm.seq2dicts('a', [1,2,3])
    >>> x
    [{'x': 1}, {'x': 2}, {'x': 3}]
    >>> y=bm.seq2dicts('y', ['xx','yy','zz'])
    >>> y
    [{'y': 'xx'}, {'y': 'yy'}, {'y': 'zz'}]
    >>> list(itertools.product(x,y))
    [({'x': 1}, {'y': 'xx'}),
     ({'x': 1}, {'y': 'yy'}),
     ({'x': 1}, {'y': 'zz'}),
     ({'x': 2}, {'y': 'xx'}),
     ({'x': 2}, {'y': 'yy'}),
     ({'x': 2}, {'y': 'zz'}),
     ({'x': 3}, {'y': 'xx'}),
     ({'x': 3}, {'y': 'yy'}),
     ({'x': 3}, {'y': 'zz'})]

    >>> bm.loops2params(itertools.product(x,y))
    [{'x': 1, 'y': 'xx'},
     {'x': 1, 'y': 'yy'},
     {'x': 1, 'y': 'zz'},
     {'x': 2, 'y': 'xx'},
     {'x': 2, 'y': 'yy'},
     {'x': 2, 'y': 'zz'},
     {'x': 3, 'y': 'xx'},
     {'x': 3, 'y': 'yy'},
     {'x': 3, 'y': 'zz'}]

The logic of the param study is entirely contained in the creation of `params`.
E.g., if parameters shall be varied together, simply use ``mkparams(zip(x,y),
z)``. The nestings from zip() are flattened in loops2params().

    >>> z=bm.seq2dicts('z', [None, 1.2, 'X'])
    >>> z
    [{'z': None}, {'z': 1.2}, {'z': 'X'}]
    >>> list(itertools.product(zip(x,y),z))
    [(({'x': 1}, {'y': 'xx'}), {'z': None}),
     (({'x': 1}, {'y': 'xx'}), {'z': 1.2}),
     (({'x': 1}, {'y': 'xx'}), {'z': 'X'}),
     (({'x': 2}, {'y': 'yy'}), {'z': None}),
     (({'x': 2}, {'y': 'yy'}), {'z': 1.2}),
     (({'x': 2}, {'y': 'yy'}), {'z': 'X'}),
     (({'x': 3}, {'y': 'zz'}), {'z': None}),
     (({'x': 3}, {'y': 'zz'}), {'z': 1.2}),
     (({'x': 3}, {'y': 'zz'}), {'z': 'X'})]

    >>> bm.loops2params(itertools.product(zip(x,y),z))
    [{'x': 1, 'y': 'xx', 'z': None},
     {'x': 1, 'y': 'xx', 'z': 1.2},
     {'x': 1, 'y': 'xx', 'z': 'X'},
     {'x': 2, 'y': 'yy', 'z': None},
     {'x': 2, 'y': 'yy', 'z': 1.2},
     {'x': 2, 'y': 'yy', 'z': 'X'},
     {'x': 3, 'y': 'zz', 'z': None},
     {'x': 3, 'y': 'zz', 'z': 1.2},
     {'x': 3, 'y': 'zz', 'z': 'X'}]

If you want a parameter which is constant, use a length one list and put it in
the loops:

    >>> c=bm.seq2dicts('c', ['const'])
    >>> bm.loops2params(itertools.product(zip(x,y),z,c))
    [{'a': 1, 'c': 'const', 'y': 'xx', 'z': None},
     {'a': 1, 'c': 'const', 'y': 'xx', 'z': 1.2},
     {'a': 1, 'c': 'const', 'y': 'xx', 'z': 'X'},
     {'a': 2, 'c': 'const', 'y': 'yy', 'z': None},
     {'a': 2, 'c': 'const', 'y': 'yy', 'z': 1.2},
     {'a': 2, 'c': 'const', 'y': 'yy', 'z': 'X'},
     {'a': 3, 'c': 'const', 'y': 'zz', 'z': None},
     {'a': 3, 'c': 'const', 'y': 'zz', 'z': 1.2},
     {'a': 3, 'c': 'const', 'y': 'zz', 'z': 'X'}]

Then we define a callback function `func`, which takes only one parameter dict
``{'a': 1, 'b': 'xx'}``, runs the benchmark and returns a dict ``{'timing':
1.234}``, which gets merged with the current parameter dict and appended to the
DataFrame. `func` is called on all `params` in the `run` helper function.
"""

from io import IOBase
from itertools import product
import timeit, os, copy
from tempfile import mkdtemp

import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

from findsame.common import KiB, MiB, GiB, size2str
pj = os.path.join


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
            _ = iter(seq)
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
    return loops2params(product(*args))


def loops2params(loops):
    return [merge_dicts(flatten(entry)) for entry in loops]


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

def bytes_logspace(start, stop, num):
    return np.unique(np.logspace(np.log10(start),
                                 np.log10(stop),
                                 num).astype(int))


def bytes_linspace(start, stop, num):
    return np.unique(np.linspace(start,
                                 stop,
                                 num).astype(int))


def write(fn, size):
    data = b'x'*size
    with open(fn, 'wb') as fd:
        fd.write(data)


def write_single_files(testdir, sizes):
    files = []
    for filesize in sizes:
        filesize_str = size2str(filesize)
        dr = pj(testdir, 'filesize_{}'.format(filesize_str))
        os.makedirs(dr, exist_ok=True)
        fn = pj(dr, 'file')
        write(fn, filesize)
        files.append(fn)
    return files


def write_file_groups(testdir, sizes, group_size=None):
    if group_size is None:
        group_size = max(sizes)
    else:
        assert group_size >= max(sizes)
    print("writing file groups, group_size: {}".format(size2str(group_size)))
    group_dirs = []
    for _filesize in sizes:
        filesize = int(_filesize)
        filesize_str = size2str(filesize)
        print("  filesize: {}".format(filesize_str))
        dr = pj(testdir, 'filesize_{}'.format(filesize_str))
        group_dirs.append(dr)
        if not os.path.exists(dr):
            os.makedirs(dr, exist_ok=True)
            nfiles = int(group_size) // filesize
            for idx in range(nfiles):
                write(pj(dr, 'file_{}'.format(idx)), filesize)
        else:
            print('    dir already present: {}'.format(dr))
    return group_dirs


def func(dct, stmt=None, setup=None):
    timing = timeit.repeat(stmt.format(**dct),
                           setup,
                           repeat=3,
                           number=1)
    return {'timing': min(timing)}


def params_filter(params):
    return [p for p in params if p['blocksize'] <= p['filesize']]


def plot(study, df, xprop, yprop, cprop=None, plot='plot'):
    fig,ax = plt.subplots()
    xticks = []
    xticklabels = []
    df = df.sort_values(xprop)
    df = df[df['study'] == study]
    if cprop is None:
        cprop = 'study'
        const_itr = [study]
    else:
        const_itr = df[cprop].unique()
    for const in const_itr:
        msk = df[cprop] == const
        label = df[msk][cprop].values[0]
        x = df[msk][xprop]
        y = df[msk][yprop]
        getattr(ax, plot)(x, y, 'o-', label=label)
        if len(x) > len(xticks):
            xticks = x
            xprop_str = xprop + '_str'
            sel = xprop_str if xprop_str in df[msk].columns else xprop
            xticklabels = df[msk][sel]

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels, rotation=45)
    ax.set_xlabel(xprop)
    ax.set_ylabel(yprop)
    ax.set_title(study)
    fig.subplots_adjust(bottom=0.2)
    ax.legend(title=cprop.replace('_str',''))


def main(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)

    setup = "from findsame import findsame as fs"
    stmt = "fs.main({files_dirs}, ncores={ncores}, blocksize={blocksize})"

    df = pd.DataFrame()
    params = []
    scale = 1
    
    # single files, test filesize and blocksize
    cases = [(bytes_linspace(10*MiB, 100*MiB, 4),
              bytes_logspace(10*KiB, 100*MiB, 10),
              'blocksize_single'),
             (bytes_linspace(10*KiB, 100*MiB, 10),
              bytes_logspace(10*MiB, 100*MiB, 4),
              'filesize_single'),
              ]

    for _filesize, _blocksize, study in cases:
        filesize = (_filesize * scale).astype(int)
        blocksize = (_blocksize * scale).astype(int)
        testdir = mkdtemp(dir=tmpdir, prefix=study)
        files = write_single_files(testdir, filesize)
        this = mkparams(zip(seq2dicts('filesize', filesize),
                            seq2dicts('filesize_str', list(map(size2str,
                                                               filesize))),
                            seq2dicts('files_dirs', [[x] for x in files])),
                        seq2dicts('study', [study]),
                        seq2dicts('ncores', [1]),
                        zip(seq2dicts('blocksize', blocksize),
                            seq2dicts('blocksize_str', list(map(size2str,
                                                                blocksize)))))
        params += this
    
    
    # collection of different file sizes (a.k.a. "realistic" synthetic data),
    # test blocksize, use the whole "testdir" as argument for findsame 
    collection_size = GiB
    ngroups = 30
    study = 'blocksize_collection'
    filesize = bytes_linspace(scale*128*KiB, scale*collection_size/ngroups, ngroups)
    blocksize = bytes_logspace(scale*10*KiB, scale*100*MiB, 10)
    testdir = mkdtemp(dir=tmpdir, prefix=study)
    write_file_groups(testdir, filesize,
                      int(collection_size/ngroups*scale))

    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    seq2dicts('ncores', [1]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this

    # same collection as above, test ncores, using the "best" blocksize
    blocksize = [256*KiB]
    study = 'ncores'
    # re-use files from above
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    seq2dicts('ncores', [1,2,4]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this

    return run(df, lambda p: func(p, stmt, setup), params)


if __name__ == '__main__':
    tmpdir = './files'
    results = './results.json'
    if os.path.exists(results):
        print("{} found, just plotting".format(results))
        df = pd.io.json.read_json(results)
    else:
        print("running benchmark")
        df = main(tmpdir)
        df.to_json(results)

    plot('blocksize_single', df, 'blocksize', 'timing', 'filesize_str', plot='semilogx')
    plot('filesize_single', df, 'filesize', 'timing', 'blocksize_str')
    plot('blocksize_collection', df, 'blocksize', 'timing', plot='semilogx')
    plot('ncores', df, 'ncores', 'timing', 'blocksize_str')

    plt.show()

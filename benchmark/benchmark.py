#!/usr/bin/env python3

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

    >>> import itertools
    >>> x=seq2dicts('a', [1,2,3])
    >>> x
    [{'x': 1}, {'x': 2}, {'x': 3}]
    >>> y=seq2dicts('y', ['xx','yy','zz'])
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

    >>> loops2params(itertools.product(x,y))
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

    >>> z=seq2dicts('z', [None, 1.2, 'X'])
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

    >>> loops2params(itertools.product(zip(x,y),z))
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

    >>> c=seq2dicts('c', ['const'])
    >>> loops2params(itertools.product(zip(x,y),z,c))
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

from itertools import product
import timeit, os, copy, sys
from tempfile import mkdtemp

import pandas as pd
import numpy as np

try:
    from matplotlib import pyplot as plt
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False

from findsame.lib.common import KiB, MiB, GiB, size2str, seq2dicts
import findsame.lib.common as co 
pj = os.path.join


#------------------------------------------------------------------------------
# general helpers
#------------------------------------------------------------------------------

def params2df(params):
    df = pd.DataFrame()
    for idx,dct in enumerate(params):
        df = df.append(pd.DataFrame(dct, index=[idx]))
    return df


def mkparams(*args):
    return loops2params(product(*args))


def loops2params(loops):
    return [co.merge_dicts(co.flatten(entry)) for entry in loops]


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
        dr = pj(testdir, 'filesize_{}'.format(size2str(filesize)))
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
    
    ylabel = 'timing (s)' if yprop == 'timing' else yprop
    rotation = 45 if xprop.endswith('size') else None
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels, rotation=rotation)
    ax.set_xlabel(xprop)
    ax.set_ylabel(ylabel)
    ax.set_title(study)
    fig.subplots_adjust(bottom=0.2)
    ax.legend(title=cprop.replace('_str',''))
    os.makedirs('pics', exist_ok=True)
    for ext in ['pdf', 'png']:
        fig.savefig("pics/{study}.{ext}".format(study=study, ext=ext), dpi=300)


def main(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)

    setup = "from findsame import fs"
    stmt = """fs.main({files_dirs}, nworkers={nworkers}, parallel='{parallel}',
                      blocksize={blocksize})"""

    df = pd.DataFrame()
    params = []
    
    # single files, test filesize and blocksize
    cases = [(np.array([500*MiB]),
              bytes_logspace(10*KiB, 200*MiB, 20),
              'blocksize_single'),
             (bytes_linspace(10*MiB, 200*MiB, 5),
              np.array([256*KiB]),
              'filesize_single'),
              ]

    for filesize, blocksize, study in cases:
        testdir = mkdtemp(dir=tmpdir, prefix=study)
        files = write_single_files(testdir, filesize)
        this = mkparams(zip(seq2dicts('filesize', filesize),
                            seq2dicts('filesize_str', list(map(size2str,
                                                               filesize))),
                            seq2dicts('files_dirs', [[x] for x in files])),
                        seq2dicts('study', [study]),
                        seq2dicts('nworkers', [1]),
                        seq2dicts('parallel', ['threads']),
                        zip(seq2dicts('blocksize', blocksize),
                            seq2dicts('blocksize_str', list(map(size2str,
                                                                blocksize)))))
        params += this
    
    
    # collection of different file sizes (a.k.a. "realistic" synthetic data),
    # test blocksize, use the whole "testdir" as argument for findsame 
    collection_size = GiB
    ngroups = 10 
    study = 'blocksize_collection'
    filesize = bytes_logspace(128*KiB, collection_size/ngroups,
                              ngroups)
    blocksize = bytes_logspace(10*KiB, 200*MiB, 20)
    testdir = mkdtemp(dir=tmpdir, prefix=study)
    write_file_groups(testdir, filesize,
                      int(collection_size/ngroups))

    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    seq2dicts('nworkers', [1]),
                    seq2dicts('parallel', ['threads']),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this

    # same collection as above, test nworkers, using the "best" blocksize
    blocksize = np.array([256*KiB])
    if sys.platform == 'freebsd10':
        parallel = ['threads']
    else:
        parallel = ['threads', 'procs']
    # re-use files from above
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    zip(seq2dicts('study', parallel),
                        seq2dicts('parallel', parallel)),
                    seq2dicts('nworkers', [1,2,3,4,5,6,7,8]),
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
    
    if HAVE_MPL:
        plot('blocksize_single', df, 'blocksize', 'timing', 'filesize_str', plot='semilogx')
        plot('filesize_single', df, 'filesize', 'timing', 'blocksize_str')
        plot('blocksize_collection', df, 'blocksize', 'timing', plot='semilogx')
        plot('threads', df, 'nworkers', 'timing', 'blocksize_str')
        plot('procs', df, 'nworkers', 'timing', 'blocksize_str')
        plt.show()

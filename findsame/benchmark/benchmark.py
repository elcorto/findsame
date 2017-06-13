#!/usr/bin/env python3

import timeit, os, sys
from tempfile import mkdtemp

import pandas as pd
import numpy as np

try:
    from matplotlib import pyplot as plt
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False

from findsame import parallel as pl 
from psweep.psweep import seq2dicts, run, loops2params
from itertools import product
from findsame.common import KiB, MiB, GiB, size2str
from findsame import calc
pj = os.path.join


def mkparams(*args):
    return loops2params(product(*args))


def bytes_logspace(start, stop, num):
    return np.unique(np.logspace(np.log10(start),
                                 np.log10(stop),
                                 num).astype(int))


def bytes_linspace(start, stop, num):
    return np.unique(np.linspace(start,
                                 stop,
                                 num).astype(int))


def write(fn, size):
    """Write a single file of `size` in bytes to path `fn`."""
    data = b'x'*size
    with open(fn, 'wb') as fd:
        fd.write(data)


def write_single_files(testdir, sizes):
    """Wite ``len(sizes)`` files to ``{testdir}/filesize_{size}/file``. Each
    file has ``sizes[i]`` in bytes. Return a list of file names."""
    files = []
    for filesize in sizes:
        dr = pj(testdir, 'filesize_{}'.format(size2str(filesize)))
        os.makedirs(dr, exist_ok=True)
        fn = pj(dr, 'file')
        write(fn, filesize)
        files.append(fn)
    return files


def write_file_groups(testdir, sizes, group_size=None):
    """For each file size (bytes) in `sizes`, write a group of ``nfiles`` files
    ``{testdir}/filesize_{size}/file_{idx}; idx=0...nfiles-1``, such that each
    dir ``filesize_{size}`` has approimately ``group_size``. If `group_size` is
    ommitted, then use ``group_size=max(size)`` such that the the group with
    the largest file ``size`` has only one file. Returns lists of group dirs
    and file names."""
    if group_size is None:
        group_size = max(sizes)
    else:
        assert group_size >= max(sizes)
    print("writing file groups, group_size: {}".format(size2str(group_size)))
    group_dirs = []
    files = []
    for _filesize in sizes:
        filesize = int(_filesize)
        filesize_str = size2str(filesize)
        print("  filesize: {}".format(filesize_str))
        dr = pj(testdir, 'filesize_{}'.format(filesize_str))
        group_dirs.append(dr)
        if not os.path.exists(dr):
            os.makedirs(dr, exist_ok=True)
            nfiles = int(group_size) // filesize
            assert nfiles >= 1
            for idx in range(nfiles):
                fn = pj(dr, 'file_{}'.format(idx))
                write(fn, filesize)
                files.append(fn)
        else:
            print('    dir already present: {}'.format(dr))
    return group_dirs, files


def write_collection(collection_size=GiB, tmpdir=None, study=None, ngroups=10):
    filesize = bytes_logspace(128*KiB, collection_size/ngroups,
                              ngroups)
    testdir = mkdtemp(dir=tmpdir, prefix=study)
    group_dirs, files = write_file_groups(testdir, filesize,
                                          int(collection_size/ngroups))
    return testdir, group_dirs, files



def func(dct, stmt=None, setup=None):
    """Callback func for psweep.run()."""
    timing = timeit.repeat(stmt.format(**dct),
                           setup,
                           repeat=3,
                           number=1)
    return {'timing': min(timing)}


def plot(study, df, xprop, yprop, cprop=None, plot='plot'):
    df = df.sort_values(xprop)
    df = df[df['study'] == study]
    if cprop is None:
        cprop = 'study'
        const_itr = [study]
    else:
        const_itr = df[cprop].unique()
    fig,ax = plt.subplots()
    xticks = []
    xticklabels = []
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


def bench_main_blocksize_filesize(tmpdir):
    setup = "from findsame import main"
    stmt = """main.main({files_dirs}, blocksize={blocksize})"""

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
                            seq2dicts('filesize_str', map(size2str,
                                                          filesize)),
                            seq2dicts('files_dirs', [[x] for x in files])),
                        seq2dicts('study', [study]),
                        zip(seq2dicts('blocksize', blocksize),
                            seq2dicts('blocksize_str', map(size2str,
                                                           blocksize))))
        params += this
    
    study = 'blocksize_collection'
    testdir, group_dirs, files = write_collection(GiB, tmpdir=tmpdir, 
                                                  study=study)
    blocksize = bytes_logspace(10*KiB, 200*MiB, 20)

    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', map(size2str,
                                                       blocksize))))
    params += this

    df = run(df, lambda p: func(p, stmt, setup), params)
    if HAVE_MPL:
        plot('blocksize_single', df, 'blocksize', 'timing', 'filesize_str', plot='semilogx')
        plot('filesize_single', df, 'filesize', 'timing', 'blocksize_str')
        plot('blocksize_collection', df, 'blocksize', 'timing', plot='semilogx')
        plt.show()
    return df


def bench_main_parallel(tmpdir):
    setup = "from findsame import main"
    stmt = """main.main({files_dirs}, blocksize={blocksize},
                        nthreads={nthreads}, nprocs={nprocs})"""

    df = pd.DataFrame()
    params = []
    
    study = 'collection_main_parallel'
    testdir, group_dirs, files = write_collection(GiB, tmpdir=tmpdir, 
                                                  study=study)
    blocksize = np.array([256*KiB])

    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', ['main_parallel']),
                    zip(seq2dicts('nthreads', range(1,6)),
                        seq2dicts('nworkers', range(1,6))),
                    seq2dicts('nprocs', [1]),
                    seq2dicts('pool_type', ['thread']),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', ['main_parallel']),
                    zip(seq2dicts('nprocs', range(1,6)),
                        seq2dicts('nworkers', range(1,6))),
                    seq2dicts('nthreads', [1]),
                    seq2dicts('pool_type', ['proc']),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this

    df = run(df, lambda p: func(p, stmt, setup), params)
    if HAVE_MPL:
        plot('main_parallel', df, 'nworkers', 'timing', 'pool_type')
        plt.show()
    return df


def bench_main_parallel_2d(tmpdir):
    setup = "from findsame import main"
    stmt = """main.main({files_dirs}, blocksize={blocksize},
                        nthreads={nthreads}, nprocs={nprocs})"""

    df = pd.DataFrame()
    params = []
    
    study = 'collection_main_parallel_2d'
    testdir, group_dirs, files = write_collection(GiB, tmpdir=tmpdir, 
                                                  study=study)
    blocksize = np.array([256*KiB])

    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', ['main_parallel']),
                    seq2dicts('nthreads', range(1,6)),
                    seq2dicts('nprocs', range(1,6)),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this

    df = run(df, lambda p: func(p, stmt, setup), params)
    if HAVE_MPL:
        from mpl_toolkits.mplot3d import Axes3D
        xx = df.nprocs.values
        yy = df.nthreads.values
        zz = df.timing.values
        x = np.unique(xx)
        y = np.unique(yy)
        X,Y = np.meshgrid(x, y, indexing='ij');
        Z = zz.reshape((len(x),len(y))).T
        fig, ax = plt.subplots(subplot_kw=dict(projection='3d'))
        ax.set_xlabel('procs')
        ax.set_ylabel('threads') 
        ax.plot_wireframe(X,Y,Z)
        ax.scatter(xx, yy, zz)
        plt.show()
    return df



def worker_bench_hash_file_parallel(fn):
    return calc.hash_file(fn, blocksize=256*KiB)


def bench_hash_file_parallel(tmpdir):
    df = pd.DataFrame()
    params = []

    study = 'parallel'
    testdir, group_dirs, files = write_collection(GiB, tmpdir=tmpdir, 
                                                  study=study)
   
    pool_map = {'seq': pl.SequentialPoolExecutor,
                'thread': pl.ThreadPoolExecutor,
                'proc': pl.ProcessPoolExecutor,
                'proc,thread=1': lambda nw: pl.ProcessAndThreadPoolExecutor(nw, 1),
                'thread,proc=1': lambda nw: pl.ProcessAndThreadPoolExecutor(1, nw),
                }
    
    def func(dct, stmt=None):
        ctx = dict(pool_map=pool_map,
                   pl=pl,
                   files=files,
                   worker=worker_bench_hash_file_parallel,
                   )
        timing = timeit.repeat(stmt.format(**dct),
                               setup='pass',
                               repeat=3,
                               number=1,
                               globals=ctx)
        return {'timing': min(timing)}

    stmt = """
with pool_map['{pool_type}']({nworkers}) as pool:
    x=list(pool.map(worker, files))
    """

    this = mkparams(seq2dicts('pool_type', 
                              [k for k in pool_map.keys() if k != 'seq']),
                    seq2dicts('nworkers', [1,2,3,4,5]),
                    [{'study': study}],
                    )
    params += this
    # non-pool reference
    params += [{'study': study, 'pool_type': 'seq', 'nworkers': 1}]

    df = run(df, lambda p: func(p, stmt), params)
    if HAVE_MPL:
        plot('parallel', df, 'nworkers', 'timing', 'pool_type')
        plt.show()
        
    return df


def update(df1, df2):
    return df1.append(df2, ignore_index=True)

if __name__ == '__main__':
    tmpdir = './files'
    results = './results.json'
    os.makedirs(tmpdir, exist_ok=True)
    df = pd.DataFrame()
    df = update(df, bench_main_blocksize_filesize(tmpdir))
    df = update(df, bench_hash_file_parallel(tmpdir))
    df = update(df, bench_main_parallel(tmpdir))
    df = update(df, bench_main_parallel_2d(tmpdir))
    df.to_json(results, orient='split')

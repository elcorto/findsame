#!/usr/bin/env python3

import timeit, os, sys
from tempfile import mkdtemp

import pandas as pd
import numpy as np

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
    data = b'x'*int(size)
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


def bench_main_blocksize_filesize(tmpdir, maxsize):
    setup = "from findsame import main"
    stmt = """main.main({files_dirs}, blocksize={blocksize})"""
    params = []
    
    # single files, test filesize and blocksize
    max_filesize = maxsize
    max_blocksize = min(200*MiB, max_filesize)
    cases = [(np.array([max_filesize]),
              bytes_logspace(10*KiB, max_blocksize, 20),
              'main_blocksize_single'),
             (bytes_linspace(10*MiB, max_filesize, 5),
              np.array([256*KiB]),
              'main_filesize_single'),
              ]

    for filesize, blocksize, study in cases:
        testdir = mkdtemp(dir=tmpdir, prefix=study)
        files = write_single_files(testdir, filesize)
        this = mkparams(zip(seq2dicts('filesize', filesize),
                            seq2dicts('filesize_str', map(size2str,
                                                          filesize)),
                            seq2dicts('files_dirs', [[x] for x in files])),
                        seq2dicts('study', [study]),
                        seq2dicts('maxsize_str', [size2str(maxsize)]),
                        zip(seq2dicts('blocksize', blocksize),
                            seq2dicts('blocksize_str', map(size2str,
                                                           blocksize))))
        params += this
    
    study = 'main_blocksize'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir, 
                                                  study=study)
    blocksize = bytes_logspace(10*KiB, min(200*MiB, maxsize), 20)
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    seq2dicts('maxsize_str', [size2str(maxsize)]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', map(size2str,
                                                       blocksize))))
    params += this
    df = pd.DataFrame()
    df = run(df, lambda p: func(p, stmt, setup), params)
    return df


def bench_main_parallel(tmpdir, maxsize):
    setup = "from findsame import main"
    stmt = """main.main({files_dirs}, blocksize={blocksize},
                        nthreads={nthreads}, nprocs={nprocs})"""
    params = []
    
    study = 'main_parallel'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir, 
                                                  study=study)
    blocksize = np.array([256*KiB])
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    zip(seq2dicts('nthreads', range(1,6)),
                        seq2dicts('nworkers', range(1,6))),
                    seq2dicts('nprocs', [1]),
                    seq2dicts('pool_type', ['thread']),
                    seq2dicts('maxsize_str', [size2str(maxsize)]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this
    
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    zip(seq2dicts('nprocs', range(1,6)),
                        seq2dicts('nworkers', range(1,6))),
                    seq2dicts('nthreads', [1]),
                    seq2dicts('pool_type', ['proc']),
                    seq2dicts('maxsize_str', [size2str(maxsize)]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this

    df = pd.DataFrame()
    df = run(df, lambda p: func(p, stmt, setup), params)
    return df


def bench_main_parallel_2d(tmpdir, maxsize):
    setup = "from findsame import main"
    stmt = """main.main({files_dirs}, blocksize={blocksize},
                        nthreads={nthreads}, nprocs={nprocs})"""

    params = []
    
    study = 'main_parallel_2d'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir, 
                                                  study=study)
    blocksize = np.array([256*KiB])
    this = mkparams(seq2dicts('files_dirs', [[testdir]]),
                    seq2dicts('study', [study]),
                    seq2dicts('nthreads', range(1,6)),
                    seq2dicts('nprocs', range(1,6)),
                    seq2dicts('maxsize_str', [size2str(maxsize)]),
                    zip(seq2dicts('blocksize', blocksize),
                        seq2dicts('blocksize_str', list(map(size2str,
                                                            blocksize)))))
    params += this

    df = pd.DataFrame()
    df = run(df, lambda p: func(p, stmt, setup), params)
    return df


def worker_bench_hash_file_parallel(fn):
    return calc.hash_file(fn, blocksize=256*KiB)


def bench_hash_file_parallel(tmpdir, maxsize):
    params = []

    study = 'hash_file_parallel'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir, 
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
                    seq2dicts('nworkers', range(1,6)),
                    seq2dicts('study', [study]),
                    seq2dicts('maxsize_str', [size2str(maxsize)]),
                    )
    params += this
    # non-pool reference
    params += [{'study': study, 'pool_type': 'seq', 'nworkers': 1, 
                'maxsize_str': size2str(maxsize)}]

    df = pd.DataFrame()
    df = run(df, lambda p: func(p, stmt), params)
    return df


def update(df1, df2):
    return df1.append(df2, ignore_index=True)


if __name__ == '__main__':
    tmpdir = './files'
    results = './results.json'
    os.makedirs(tmpdir, exist_ok=True)
    df = pd.DataFrame()
    for maxsize in [GiB, 2*GiB]:
        df = update(df, bench_main_blocksize_filesize(tmpdir, maxsize))
        df = update(df, bench_hash_file_parallel(tmpdir, maxsize))
        df = update(df, bench_main_parallel(tmpdir, maxsize))
        df = update(df, bench_main_parallel_2d(tmpdir, maxsize))
    df.to_json(results, orient='split')

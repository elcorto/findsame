#!/usr/bin/env python3

import timeit, os, sys, shutil, textwrap
from tempfile import mkdtemp

import pandas as pd
import numpy as np

from findsame import parallel as pl
from psweep import psweep as ps
from itertools import product
from findsame.common import KiB, MiB, GiB, size2str
from findsame import calc
pj = os.path.join


default_setup = textwrap.dedent("""
    from findsame import main
    from findsame.config import cfg
    """)


def mkparams(*args):
    return ps.loops2params(product(*args))


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
        dr = pj(testdir, f'filesize_{size2str(filesize)}')
        os.makedirs(dr, exist_ok=True)
        fn = pj(dr, 'file')
        write(fn, filesize)
        files.append(fn)
    return files


def write_file_groups(testdir, sizes, group_size=None):
    """For each file size (bytes) in `sizes`, write a group of ``nfiles`` files
    ``{testdir}/filesize_{size}/file_{idx}; idx=0...nfiles-1``, such that each
    dir ``filesize_{size}`` has approximately ``group_size``. If `group_size`
    is omitted, then use ``group_size=max(sizes)`` such that the the group with
    the largest file size has only one file. Returns lists of group dirs
    and file names."""
    if group_size is None:
        group_size = max(sizes)
    else:
        assert group_size >= max(sizes)
    group_dirs = []
    files = []
    for _filesize in sizes:
        filesize = int(_filesize)
        filesize_str = size2str(filesize)
        dr = pj(testdir, f'filesize_{filesize_str}')
        group_dirs.append(dr)
        if not os.path.exists(dr):
            os.makedirs(dr, exist_ok=True)
            nfiles = int(group_size) // filesize
            assert nfiles >= 1
            for idx in range(nfiles):
                fn = pj(dr, f'file_{idx}')
                write(fn, filesize)
                files.append(fn)
        else:
            print(f'    dir already present: {dr}')
    return group_dirs, files


def write_collection(collection_size=GiB, min_size=128*KiB, tmpdir=None,
                     study=None, ngroups=100):
    """Special-purpose version of write_file_groups().

    Write a collection of ``ngroups`` file groups, such that the whole
    collection has approximately ``collection_size``. Each group has equal
    group size of ``collection_size/ngroups`` and an automatically determined
    file size, such that groups with a small file size have many files, while
    groups with large file size have few files.

    This is used to create a syntetic real-wold-like file distribution on a
    system with many small and few large files.
    """
    group_size = int(collection_size/ngroups)
    assert group_size > 0
    filesize = bytes_logspace(min_size,group_size, ngroups)
    os.makedirs(tmpdir, exist_ok=True)
    testdir = mkdtemp(dir=tmpdir, prefix=study + '_')
    group_dirs, files = write_file_groups(testdir, filesize,
                                          group_size)
    return testdir, group_dirs, files


def psweep_callback(dct, stmt=None, setup=None, ctx=None):
    """Default callback func for psweep.run()."""
    timing = timeit.repeat(stmt.format(**dct),
                           setup,
                           repeat=3,
                           number=1,
                           globals=ctx)
    return {'timing': min(timing)}


def bench_main_blocksize_filesize(tmpdir, maxsize):
    stmt = textwrap.dedent("""
        cfg.update(dict(blocksize={blocksize}))
        main.main({files_dirs})
        """)
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
        testdir = mkdtemp(dir=tmpdir, prefix=study + '_')
        files = write_single_files(testdir, filesize)
        this = mkparams(zip(ps.seq2dicts('filesize', filesize),
                            ps.seq2dicts('filesize_str', map(size2str,
                                                             filesize)),
                            ps.seq2dicts('files_dirs', [[x] for x in files])),
                        ps.seq2dicts('study', [study]),
                        ps.seq2dicts('maxsize_str', [size2str(maxsize)]),
                        zip(ps.seq2dicts('blocksize', blocksize),
                            ps.seq2dicts('blocksize_str', map(size2str,
                                                              blocksize))))
        params += this

    study = 'main_blocksize'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir,
                                                  study=study)
    blocksize = bytes_logspace(10*KiB, min(200*MiB, maxsize), 20)
    this = mkparams(ps.seq2dicts('files_dirs', [[testdir]]),
                    ps.seq2dicts('study', [study]),
                    ps.seq2dicts('maxsize_str', [size2str(maxsize)]),
                    zip(ps.seq2dicts('blocksize', blocksize),
                        ps.seq2dicts('blocksize_str', map(size2str,
                                                          blocksize))))
    params += this
    return None, stmt, None, params


def bench_main_parallel(tmpdir, maxsize):
    stmt = textwrap.dedent("""
        cfg.update(dict(blocksize={blocksize},
                        nthreads={nthreads},
                        nprocs={nprocs},
                        share_leafs={share_leafs}))
        main.main({files_dirs})
        """)
    params = []

    study = 'main_parallel'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir,
                                                  study=study)
    blocksize = np.array([256*KiB])

    for share_leafs in [True, False]:
        this = mkparams(ps.seq2dicts('files_dirs', [[testdir]]),
                        ps.seq2dicts('study', [study]),
                        zip(ps.seq2dicts('nthreads', range(1, MAXWORKERS+1)),
                            ps.seq2dicts('nworkers', range(1, MAXWORKERS+1))),
                        ps.seq2dicts('nprocs', [1]),
                        ps.seq2dicts('pool_type', ['thread']),
                        ps.seq2dicts('maxsize_str', [size2str(maxsize)]),
                        ps.seq2dicts('share_leafs', [share_leafs]),
                        zip(ps.seq2dicts('blocksize', blocksize),
                            ps.seq2dicts('blocksize_str', list(map(size2str,
                                                                   blocksize)))))
        params += this

        this = mkparams(ps.seq2dicts('files_dirs', [[testdir]]),
                        ps.seq2dicts('study', [study]),
                        zip(ps.seq2dicts('nprocs', range(1, MAXWORKERS+1)),
                            ps.seq2dicts('nworkers', range(1, MAXWORKERS+1))),
                        ps.seq2dicts('nthreads', [1]),
                        ps.seq2dicts('pool_type', ['proc']),
                        ps.seq2dicts('maxsize_str', [size2str(maxsize)]),
                        ps.seq2dicts('share_leafs', [share_leafs]),
                        zip(ps.seq2dicts('blocksize', blocksize),
                            ps.seq2dicts('blocksize_str', list(map(size2str,
                                                                   blocksize)))))
        params += this
    return None, stmt, None, params


def bench_main_parallel_2d(tmpdir, maxsize):
    stmt = textwrap.dedent("""
        cfg.update(dict(blocksize={blocksize},
                        nthreads={nthreads},
                        nprocs={nprocs}))
        main.main({files_dirs})
        """)
    params = []

    study = 'main_parallel_2d'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir,
                                                  study=study)
    blocksize = np.array([256*KiB])
    this = mkparams(ps.seq2dicts('files_dirs', [[testdir]]),
                    ps.seq2dicts('study', [study]),
                    ps.seq2dicts('nthreads', range(1, MAXWORKERS+1)),
                    ps.seq2dicts('nprocs', range(1, MAXWORKERS+1)),
                    ps.seq2dicts('maxsize_str', [size2str(maxsize)]),
                    zip(ps.seq2dicts('blocksize', blocksize),
                        ps.seq2dicts('blocksize_str', list(map(size2str,
                                                               blocksize)))))
    params += this
    return None, stmt, None, params


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

    def callback(dct, stmt=None, setup='pass', ctx=None):
        ctx = dict(pool_map=pool_map,
                   pl=pl,
                   files=files,
                   worker=worker_bench_hash_file_parallel,
                   )
        timing = timeit.repeat(stmt.format(**dct),
                               setup=setup,
                               repeat=3,
                               number=1,
                               globals=ctx,
                               )
        return {'timing': min(timing)}

    setup = 'pass'
    stmt = """
with pool_map['{pool_type}']({nworkers}) as pool:
    x=list(pool.map(worker, files))
    """

    this = mkparams(ps.seq2dicts('pool_type',
                                 [k for k in pool_map.keys() if k != 'seq']),
                    ps.seq2dicts('nworkers', range(1, MAXWORKERS+1)),
                    ps.seq2dicts('study', [study]),
                    ps.seq2dicts('maxsize_str', [size2str(maxsize)]),
                    )
    params += this
    # non-pool reference
    params += [{'study': study, 'pool_type': 'seq', 'nworkers': 1,
                'maxsize_str': size2str(maxsize)}]

    return callback, stmt, setup, params


def update(df1, df2):
    return df1.append(df2, ignore_index=True, sort=False)


# adapted from pwtools
def backup(src, prefix='.'):
    """Backup (copy) `src` to <src><prefix><num>, where <num> is an integer
    starting at 0 which is incremented until there is no destination with that
    name.

    Symlinks are handled by shutil.copy() for files and shutil.copytree() for
    dirs. In both cases, the content of the file/dir pointed to by the link is
    copied.

    Parameters
    ----------
    src : str
        name of file/dir to be copied
    prefix : str, optional
    """
    if os.path.exists(src):
        if os.path.isfile(src):
            copy = shutil.copy
        elif os.path.isdir(src):
            copy = shutil.copytree
        else:
            raise Exception("source '%s' is not file or dir" % src)
        idx = 0
        dst = src + '%s%s' % (prefix,idx)
        while os.path.exists(dst):
            idx += 1
            dst = src + '%s%s' % (prefix,idx)
        # sanity check
        if os.path.exists(dst):
            raise Exception("destination '%s' exists" % dst)
        else:
            copy(src, dst)


if __name__ == '__main__':
    MAXWORKERS = 6
    # usage:
    #   ./this.py [old_results.json]
    tmpdir = './files'
    results = './results.json'
    os.makedirs(tmpdir, exist_ok=True)
    bench_funcs = [
        bench_main_blocksize_filesize,
        bench_hash_file_parallel,
        bench_main_parallel,
        bench_main_parallel_2d,
        ]
    if len(sys.argv) == 2:
        df = ps.df_json_read(sys.argv[1])
    else:
        df = pd.DataFrame()
    # hack for strange FreeBSD 10.3 (FreeNAS) 2 GB file size limit issue
    if sys.platform == 'freebsd10':
        twoGB = 2*GiB-1
    else:
        twoGB = 2*GiB
    # for quick testing of this script
    for maxsize in [20*MiB]:
##    # production setting
##    for maxsize in [GiB]:
##    for maxsize in [GiB, twoGB]:
        for idx, bench_func in enumerate(bench_funcs):
            print(bench_func.__name__)
            _callback, stmt, setup, params = bench_func(tmpdir, maxsize)
            callback = psweep_callback if _callback is None else _callback
            setup = default_setup if setup is None else setup

            def func(p):
                return callback(p, stmt, setup)

            df = update(df, ps.run(func, params, poolsize=None, save=False))
            ps.df_write(df, f'save_{idx}_up_to_{bench_func.__name__}_{size2str(maxsize)}.json',
                        fmt='json')
    backup(results)
    ps.df_write(df, results, fmt='json')

#!/usr/bin/env python3

import os
import textwrap
import timeit
from tempfile import mkdtemp

import numpy as np

import psweep as ps

from findsame import parallel as pl
from findsame.common import KiB, MiB, GiB, size2str
from findsame import calc
pj = os.path.join

# Flush disk caches between runs. We use timeit.repeat(stmt, setup, repeat=3,
# number=1) which does smth like
#
#   for i in range(repeat):
#       setup
#       for j in range(number):
#           stmt
#
# so setup runs prior to each execution of stmt.
cache_flush_setup = """
from subprocess import run
run("sudo -A sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'", shell=True)
"""

# This code is executed by timeit in callback() before each benchmark run. Each
# run (bench_func) may modify cfg -- the package-wide configuration dict
# findsame.config.cfg -- before calling the package's main.main() or other
# functions. Since this script here is run by a single Python interpreter,
# changes to cfg are persistent from one bench_func to another. This is by
# design, but in this context here a subtle gotcha. Therefore, we need to reset
# cfg to default_cfg before doing anything else in each run.
default_setup = f"""
from findsame import main
from findsame.config import cfg, default_cfg

cfg.update(default_cfg)

{cache_flush_setup}
"""

#------------------------------------------------------------------------------
# helpers
#------------------------------------------------------------------------------

def psweep_callback(pset, stmt=None, **kwds):
    """Default callback func for psweep.run().

    Paremeters
    ----------
    pset : dict
    stmt : str
    kwds : for timeit.repeat
        setup, globals
    """
    if 'setup' not in kwds:
        kwds['setup'] = default_setup
    timing = timeit.repeat(stmt.format(**pset),
                           repeat=3,
                           number=1,
                           **kwds)
    return {'timing': min(timing)}


def bytes_logspace(start, stop, num):
    return np.unique(np.logspace(np.log10(start),
                                 np.log10(stop),
                                 num).astype(int))


def bytes_linspace(start, stop, num):
    return np.unique(np.linspace(start,
                                 stop,
                                 num).astype(int))


#------------------------------------------------------------------------------
# tools to generate synthetic test data
#------------------------------------------------------------------------------

def write(fn, size):
    """Write a single file of `size` in bytes to path `fn`."""
    with open(fn, 'wb') as fd:
        fd.write(os.urandom(size))


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
    is omitted, then use ``group_size=max(sizes)`` such that the group with
    the largest file size has only one file. Returns lists of group dirs
    and file names."""
    if group_size is None:
        group_size = max(sizes)
    else:
        assert group_size >= max(sizes), \
                f"{size2str(group_size)} < {size2str(max(sizes))}"
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


#------------------------------------------------------------------------------
# benchmark functions
#------------------------------------------------------------------------------


def bench_main_blocksize_filesize(tmpdir, maxsize):
    stmt = textwrap.dedent("""
        cfg.update(blocksize={blocksize})
        main.main({files_dirs})
        """)
    params = []

    # single files, test filesize and blocksize
    max_filesize = maxsize
    max_blocksize = min(200*MiB, max_filesize)
    cases = [(np.array([max_filesize]),
              bytes_logspace(10*KiB, max_blocksize, 20),
              'main_blocksize_single'),
             (bytes_linspace(min(1*MiB, max_filesize//2), max_filesize, 5),
              np.array([256*KiB]),
              'main_filesize_single'),
             ]

    for filesize, blocksize, study in cases:
        testdir = mkdtemp(dir=tmpdir, prefix=study + '_')
        files = write_single_files(testdir, filesize)
        this = ps.pgrid(zip(ps.plist('filesize', filesize),
                            ps.plist('filesize_str', map(size2str,
                                                         filesize)),
                            ps.plist('files_dirs', [[x] for x in files])),
                        ps.plist('study', [study]),
                        ps.plist('maxsize_str', [size2str(maxsize)]),
                        zip(ps.plist('blocksize', blocksize),
                            ps.plist('blocksize_str', map(size2str,
                                                          blocksize))))
        params += this

    study = 'main_blocksize'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir,
                                                  study=study)
    blocksize = bytes_logspace(10*KiB, min(200*MiB, maxsize), 20)
    this = ps.pgrid(ps.plist('files_dirs', [[testdir]]),
                    ps.plist('study', [study]),
                    ps.plist('maxsize_str', [size2str(maxsize)]),
                    zip(ps.plist('blocksize', blocksize),
                        ps.plist('blocksize_str', map(size2str,
                                                          blocksize))))
    params += this
    return stmt, params, {}


def bench_main_parallel(tmpdir, maxsize):
    stmt = textwrap.dedent("""
        cfg.update(blocksize={blocksize},
                   nthreads={nthreads},
                   nprocs={nprocs},
                   share_leafs={share_leafs})
        main.main({files_dirs})
        """)
    params = []

    study = 'main_parallel'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir,
                                                  study=study)
    blocksize = np.array([256*KiB])

    for share_leafs in [True, False]:
        this = ps.pgrid(ps.plist('files_dirs', [[testdir]]),
                        ps.plist('study', [study]),
                        zip(ps.plist('nthreads', range(1, MAXWORKERS+1)),
                            ps.plist('nworkers', range(1, MAXWORKERS+1))),
                        ps.plist('nprocs', [1]),
                        ps.plist('pool_type', ['thread']),
                        ps.plist('maxsize_str', [size2str(maxsize)]),
                        ps.plist('share_leafs', [share_leafs]),
                        zip(ps.plist('blocksize', blocksize),
                            ps.plist('blocksize_str', list(map(size2str,
                                                                   blocksize)))))
        params += this

        this = ps.pgrid(ps.plist('files_dirs', [[testdir]]),
                        ps.plist('study', [study]),
                        zip(ps.plist('nprocs', range(1, MAXWORKERS+1)),
                            ps.plist('nworkers', range(1, MAXWORKERS+1))),
                        ps.plist('nthreads', [1]),
                        ps.plist('pool_type', ['proc']),
                        ps.plist('maxsize_str', [size2str(maxsize)]),
                        ps.plist('share_leafs', [share_leafs]),
                        zip(ps.plist('blocksize', blocksize),
                            ps.plist('blocksize_str', list(map(size2str,
                                                                   blocksize)))))
        params += this
    return stmt, params, {}


def bench_main_parallel_2d(tmpdir, maxsize):
    stmt = textwrap.dedent("""
        cfg.update(blocksize={blocksize},
                   nthreads={nthreads},
                   nprocs={nprocs})
        main.main({files_dirs})
        """)
    params = []

    study = 'main_parallel_2d'
    testdir, group_dirs, files = write_collection(maxsize, tmpdir=tmpdir,
                                                  study=study)
    blocksize = np.array([256*KiB])
    this = ps.pgrid(ps.plist('files_dirs', [[testdir]]),
                    ps.plist('study', [study]),
                    ps.plist('nthreads', range(1, MAXWORKERS+1)),
                    ps.plist('nprocs', range(1, MAXWORKERS+1)),
                    ps.plist('maxsize_str', [size2str(maxsize)]),
                    zip(ps.plist('blocksize', blocksize),
                        ps.plist('blocksize_str', list(map(size2str,
                                                               blocksize)))))
    params += this
    return stmt, params, {}


def _worker_bench_hash_file_parallel(fn):
    return calc.hash_file(calc.Leaf(fn), blocksize=256*KiB)

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

    ctx = dict(pool_map=pool_map,
               pl=pl,
               files=files,
               worker=_worker_bench_hash_file_parallel,
               )

    setup = cache_flush_setup

    stmt = """
with pool_map['{pool_type}']({nworkers}) as pool:
    x=list(pool.map(worker, files))
    """

    this = ps.pgrid(ps.plist('pool_type',
                             [k for k in pool_map.keys() if k != 'seq']),
                    ps.plist('nworkers', range(1, MAXWORKERS+1)),
                    ps.plist('study', [study]),
                    ps.plist('maxsize_str', [size2str(maxsize)]),
                    )
    params += this
    # non-pool reference
    params += [{'study': study, 'pool_type': 'seq', 'nworkers': 1,
                'maxsize_str': size2str(maxsize)}]

    return stmt, params, dict(setup=setup, globals=ctx)


if __name__ == '__main__':
    MAXWORKERS = 6
    tmpdir = './files'
    os.makedirs(tmpdir, exist_ok=True)
    bench_funcs = [
        bench_main_blocksize_filesize,
        bench_hash_file_parallel,
        bench_main_parallel,
        bench_main_parallel_2d,
        ]
    # for quick testing of this script
##    for maxsize in [15*MiB]:
##    # production setting
    for maxsize in [2*GiB]:
##    for maxsize in [GiB, twoGB]:
        for bench_func in bench_funcs:
            print(bench_func.__name__)
            stmt, params, kwds = bench_func(tmpdir, maxsize)
            ps.run(lambda p: psweep_callback(p, stmt, **kwds), params)

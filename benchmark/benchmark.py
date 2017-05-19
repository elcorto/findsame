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

from findsame.benchmark import parallel as pl 
from findsame.benchmark.psweep import seq2dicts, mkparams, run
from findsame.lib.common import KiB, MiB, GiB, size2str
from findsame.lib import calc
pj = os.path.join


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
            for idx in range(nfiles):
                fn = pj(dr, 'file_{}'.format(idx))
                write(fn, filesize)
                files.append(fn)
        else:
            print('    dir already present: {}'.format(dr))
    return group_dirs, files


def func(dct, stmt=None, setup=None):
    timing = timeit.repeat(stmt.format(**dct),
                           setup,
                           repeat=3,
                           number=1)
    return {'timing': min(timing)}


def params_filter(params):
    return [p for p in params if p['blocksize'] <= p['filesize']]


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


def bench_main(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)

    setup = "from findsame import fs"
    stmt = """fs.main({files_dirs}, nworkers={nworkers}, parallel='{parallel}',
                      blocksize={blocksize})"""

    df = pd.DataFrame()
    params = []
    
##    # single files, test filesize and blocksize
##    cases = [(np.array([500*MiB]),
##              bytes_logspace(10*KiB, 200*MiB, 20),
##              'blocksize_single'),
##             (bytes_linspace(10*MiB, 200*MiB, 5),
##              np.array([256*KiB]),
##              'filesize_single'),
##              ]
##
##    for filesize, blocksize, study in cases:
##        testdir = mkdtemp(dir=tmpdir, prefix=study)
##        files = write_single_files(testdir, filesize)
##        this = mkparams(zip(seq2dicts('filesize', filesize),
##                            seq2dicts('filesize_str', list(map(size2str,
##                                                               filesize))),
##                            seq2dicts('files_dirs', [[x] for x in files])),
##                        seq2dicts('study', [study]),
##                        seq2dicts('nworkers', [1]),
##                        seq2dicts('parallel', ['threads']),
##                        zip(seq2dicts('blocksize', blocksize),
##                            seq2dicts('blocksize_str', list(map(size2str,
##                                                                blocksize)))))
##        params += this
    
    
    # collection of different file sizes (a.k.a. "realistic" synthetic data),
    # test blocksize, use the whole "testdir" as argument for findsame 
    collection_size = GiB*0.1
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
##    params += this

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

    df = run(df, lambda p: func(p, stmt, setup), params)
    if HAVE_MPL:
##        plot('blocksize_single', df, 'blocksize', 'timing', 'filesize_str', plot='semilogx')
##        plot('filesize_single', df, 'filesize', 'timing', 'blocksize_str')
##        plot('blocksize_collection', df, 'blocksize', 'timing', plot='semilogx')
        plot('threads', df, 'nworkers', 'timing', 'blocksize_str')
        plot('procs', df, 'nworkers', 'timing', 'blocksize_str')
        plt.show()
    return df


def worker_bench_parallel(fn):
    return calc.hash_file(fn, blocksize=256*KiB)
  

def bench_parallel(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)
    
    df = pd.DataFrame()
    params = []

    collection_size = GiB
    ngroups = 10 
    study = 'parallel'
    filesize = bytes_logspace(128*KiB, collection_size/ngroups,
                              ngroups)
    testdir = mkdtemp(dir=tmpdir, prefix=study)
    _, files = write_file_groups(testdir, filesize,
                                 int(collection_size/ngroups))
    
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
                   worker=worker_bench_parallel,
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
    params += [{'study': 'parallel', 'pool_type': 'seq', 'nworkers': 1}]

    df = run(df, lambda p: func(p, stmt), params)
    if HAVE_MPL:
        plot('parallel', df, 'nworkers', 'timing', 'pool_type')
        plt.show()
        
    return df

if __name__ == '__main__':
    tmpdir = './files'
    results = './results.json'
    if os.path.exists(results):
        print("{} found, just plotting".format(results))
        df = pd.io.json.read_json(results)
    else:
        print("running benchmark")
        bench_main(tmpdir).to_json(results)
##        bench_parallel(tmpdir).to_json(results)

#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, \
    Executor
import time

# TODO: investigate Executor.map(..., chunksize=N) with N>1 (default N=1)

def chop(seq, nchunks=1):
    """Chop sequence into `nchunks` apptoximately equal length chunks."""
    chunk_size = len(seq) // nchunks
    for ichunk in range(nchunks):
        aa = ichunk*chunk_size
        if ichunk < nchunks-1:
            bb = (ichunk+1)*chunk_size
        else:
            bb = None
        yield seq[slice(aa,bb)]


def test_thread_worker(item):
    print(item)
    time.sleep(1)
    return item


class SequentialPoolExecutor:
    """Fake a Pool executor with a sequential map(). Use this to get a
    sequential baseline performance w/o any thread overhead."""
    def __init__(self, *args, **kwds):
        pass

    def map(self, worker, seq):
        for item in seq:
            yield worker(item)
    
    def __enter__(self, *args):
        return self
    
    def __exit__(self, *args):
        pass


class ProcessAndThreadPoolExecutor(Executor):
    def __init__(self, nprocs, nthreads):
        self.nprocs = nprocs
        self.nthreads = nthreads
    
    def process_worker(self, sublist):
        with ThreadPoolExecutor(self.nthreads) as thread_pool:
            # Need to return a list here, else:
            #     concurrent.futures.process.BrokenProcessPool: A process in the
            #     process pool was terminated abruptly while the future was running
            #     or pending.
            # Looks like we need to force a wait for the completion of the
            # evaluation of the map() method.
            return list(thread_pool.map(self.thread_worker, sublist))

    def map(self, thread_worker, seq):
        # Cannot define process_worker inside map():
        #     AttributeError: Can't pickle local object
        #     'ProcessAndThreadPoolExecutor.map.<locals>.process_worker'"
        # Must pass thread_worker that way to process_worker.
        self.thread_worker = thread_worker
        with ProcessPoolExecutor(self.nprocs) as process_pool:
            return process_pool.map(self.process_worker, chop(seq, self.nprocs))


if __name__ == '__main__':
    lst = range(20)
    ncores = 2
    nthreads = 5
    with ProcessAndThreadPoolExecutor(ncores, nthreads) as pool:
        print(list(pool.map(test_thread_worker, lst)))

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, \
    Executor
import time
import itertools

# TODO: investigate Executor.map(..., chunksize=N) with N>1 (default N=1)


def chop(_seq, nchunks=1):
    """Chop sequence into `nchunks` chunks of approximately equal length."""
    # hack: to get the length, we have to leave the nice iterators-only land
    seq = list(_seq)
    chunk_size = len(seq) // nchunks
    for ichunk in range(nchunks):
        aa = ichunk*chunk_size
        if ichunk < nchunks-1:
            bb = (ichunk+1)*chunk_size
        else:
            bb = None
        yield itertools.islice(seq, aa, bb)


def thread_worker_example(item):
    """Example worker function for ThreadPoolExecutor."""
    print(item)
    time.sleep(1)
    return item


class SequentialPoolExecutor:
    """Fake a Pool executor with a sequential map(). Use this to get a
    sequential baseline performance w/o any thread overhead."""
    def __init__(self, *args, **kwds):
        pass

    def map(self, worker, seq, **kwds):
        for item in seq:
            yield worker(item)

    def __enter__(self, *args):
        return self

    def __exit__(self, *args):
        pass


class ProcessAndThreadPoolExecutor(Executor):
    """Split the sequence given to the map() method into self.nprocs chunks.
    Start nprocs processes, and in each start a thread pool of self.nthreads
    size to process the sub-sequence."""
    def __init__(self, nprocs, nthreads):
        self.nprocs = nprocs
        self.nthreads = nthreads

    def process_worker(self, subseq):
        """Worker function for ProcessPoolExecutor. Spawn a thread pool of
        self.nthreads size in each process."""
        with ThreadPoolExecutor(self.nthreads) as thread_pool:
            # Need to call list() here in between, else:
            #     concurrent.futures.process.BrokenProcessPool: A process in the
            #     process pool was terminated abruptly while the future was running
            #     or pending.
            # Looks like we need to force a wait for the completion of the
            # evaluation of thread_pool.map().
            return iter(list(thread_pool.map(self.thread_worker, subseq)))

    def map(self, thread_worker, seq, **kwds):
        # Cannot define process_worker inside map():
        #     AttributeError: Can't pickle local object
        #     'ProcessAndThreadPoolExecutor.map.<locals>.process_worker'"
        # Must pass thread_worker that way to process_worker.
        self.thread_worker = thread_worker
        with ProcessPoolExecutor(self.nprocs) as process_pool:
            results = process_pool.map(self.process_worker, chop(seq,
                                                                 self.nprocs), **kwds)
            return itertools.chain(*results)


if __name__ == '__main__':
    lst = range(20)
    ncores = 2
    nthreads = 5
    with ProcessAndThreadPoolExecutor(ncores, nthreads) as pool:
        print(list(pool.map(thread_worker_example, lst)))

#!/usr/bin/python3

"""
Simplified benchmark of the bottleneck: findsame.lib.calc.hash_file(). How do
we know? To get an idea of the overall code performance, we use the pprofile
line profiler and run fs.py with nworkers=1 (default)::

    $ pprofile3 ./fs.py ...
    38|     34080|     0.155238|  4.55511e-06|  0.15%|def hash_file(fn, blocksize=BLOCKSIZE):
    ....................
    58|     34079|     0.268784|  7.88709e-06|  0.26%|    hasher = hashlib.sha1()
    59|     34079|     0.746124|   2.1894e-05|  0.72%|    with open(fn, 'rb') as fd:
    60|     34079|      6.48243|  0.000190218|  6.21%|        buf = fd.read(blocksize)
    61|    142324|      1.92764|   1.3544e-05|  1.85%|        while buf:
    62|    108245|      36.0914|  0.000333424| 34.59%|            hasher.update(buf)
    63|    108245|      32.4784|  0.000300045| 31.13%|            buf = fd.read(blocksize)
    64|     34079|     0.353401|  1.03701e-05|  0.34%|    return hasher.hexdigest()

Performance is eaten 33% by I/O and 33% by hashing, the rest is general Python
slowness, but hash_file() is the hot spot with 66% runtime. So the process is
33% I/O bound?

We test parallelization of hash_file() over files. The general wisdom is that
for CPU-bound problems, we need to use proceses (ProcessPoolExecutor or
multiprocessing.Pool) to bypass the GIL. That works best for low numbers of
large chunky workloads / core (i.e. coarse-grained parallelization) b/c of
process overhead.

ATM, we cannot use ProcessPoolExecutor here in this sceipt b/c of 

    Traceback (most recent call last):
      File "/usr/lib/python3.5/multiprocessing/queues.py", line 241, in _feed
        obj = ForkingPickler.dumps(obj)
      File "/usr/lib/python3.5/multiprocessing/reduction.py", line 50, in dumps
        cls(buf, protocol).dump(obj)
    AttributeError: Can't pickle local object 'inner.<locals>.worker'

but we know from benchmark.py that we actually get a 2-fold *slowdown* (see
benchmark.py).

On the other hand, it is "well known" that one can fight I/O-bound problems
with threads. Indeed, we see a speedup of 1.5..1.6, which is a bit more than
1.33. The reason for there being a speedup at all with threads is unclear to
me. Our test system is a Core i5-3210M which has 2 threads / core. Since
threading in Python is still bound to one interpreter process by the GIL, it is
unclear where the speedup comes from. Need to test that on a system with 1
thread / core (i.e. no Intel Hyperthreading).
"""

import timeit
 
setup = """
import os, time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from findsame.benchmark import benchmark as bm
from findsame.lib.calc import hash_file

files = []
for x in range(5):
    fn = 'files/file{}'.format(x)
    if not os.path.exists(fn):
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        bm.write(fn, 50*bm.MiB)
    files.append(fn)

class SequentialPoolExecutor:
    # Fake a Pool executor with a sequential map(). Use this to get a sequential
    # baseline performance w/o any thread overhead.
    def __init__(self, *args, **kwds):
        pass

    def map(self, worker, seq):
        for item in seq:
            yield worker(item)
    
    def __enter__(self, *args):
        return self
    
    def __exit__(self, *args):
        pass

##def worker(fn):
##    with open(fn, 'rb') as fd:
##        x = fd.read()
##        time.sleep(0.5)

def worker(fn):
    return hash_file(fn)
"""
stmt_tmpl = """
##with SequentialPoolExecutor() as pool:
with ThreadPoolExecutor({nworkers}) as pool:
##with ProcessPoolExecutor({nworkers}) as pool:
   list(pool.map(worker, files))
"""

for nworkers in range(1,6):
    stmt = stmt_tmpl.format(nworkers=nworkers)
    timings = timeit.repeat(stmt, setup, number=1, repeat=5)
    print("nworkers={}: time={}".format(nworkers, min(timings)))

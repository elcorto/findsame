Simplified benchmark of the bottleneck: findsame.calc.hash_file(). How do
we know? To get an idea of the overall code performance, we use the pprofile
line profiler and run findsame with nworkers=1 (default)::

    $ pprofile3 ./findsame ...
    38|     34080|     0.155238|  4.55511e-06|  0.15%|def hash_file(fn, blocksize=BLOCKSIZE):
    ....................
    58|     34079|     0.268784|  7.88709e-06|  0.26%|    hasher = hashlib.sha1()
    59|     34079|     0.746124|   2.1894e-05|  0.72%|    with open(fn, 'rb') as fd:
    60|     34079|      6.48243|  0.000190218|  6.21%|        buf = fd.read(blocksize)
    61|    142324|      1.92764|   1.3544e-05|  1.85%|        while buf:
    62|    108245|      36.0914|  0.000333424| 34.59%|            hasher.update(buf)
    63|    108245|      32.4784|  0.000300045| 31.13%|            buf = fd.read(blocksize)
    64|     34079|     0.353401|  1.03701e-05|  0.34%|    return hasher.hexdigest()

Apparently, performance is eaten 33% by I/O and 33% by hashing, the rest is
general Python slowness, but hash_file() is the hot spot with 66% runtime. So
the process is 33% I/O bound?

We test parallelization of hash_file() over files. The general wisdom is that
for CPU-bound problems, we need to use proceses (ProcessPoolExecutor or
multiprocessing.Pool) to bypass the GIL. That works best for low numbers of
large chunky workloads per core (i.e. coarse-grained parallelization) b/c of
process overhead. With that, we get a speedup of ~1.3 .

On the other hand, it is "well known" that one can fight I/O-bound problems
with threads. Indeed, we see a speedup of 1.8! Our test system is a Core i3 or
Core i5 which has 2 threads per core. Since threading in Python is still bound
to one interpreter process by the GIL, it is at first sight unclear where the
speedup actually comes from. Rumor has it that threads waiting for IO do
actualy release the GIL. The behavior is the same on a system with 1 thread per
core (i.e. no Intel Hyperthreading).

findsame
========

Find duplicate files and directories.

As other tools we use file hashes but additionally, we report duplicate
directories as well, using a Merkle tree for directory hash calculation.

To increase performance, we use parallel hash calculation and optional limits
on to-be-hashed data.

usage
-----

::

    usage: findsame [-h] [-b BLOCKSIZE] [-l LIMIT] [-p NPROCS] [-t NTHREADS]
                    [-o OUTMODE] [-v]
                    file/dir [file/dir ...]

    Find same files and dirs based on file hashes.

    positional arguments:
      file/dir              files and/or dirs to compare

    optional arguments:
      -h, --help            show this help message and exit
      -b BLOCKSIZE, --blocksize BLOCKSIZE
                            blocksize in hash calculation, use units K,M,G as in
                            100M, 218K or just 1024 (bytes) [default: 256.0K]
      -l LIMIT, --limit LIMIT
                            read limit (bytes), same units as BLOCKSIZE, calculate
                            hash only over the first LIMIT bytes, makes things go
                            faster for may large files, try 500K [default: None]
      -p NPROCS, --nprocs NPROCS
                            number of parallel processes [default: 1]
      -t NTHREADS, --nthreads NTHREADS
                            threads per process [2]
      -o OUTMODE, --outmode OUTMODE
                            1: json, 2: json with hashes [default: 1]
      -v, --verbose         enable verbose/debugging output

The output format is json, either with or without hashes (see ``--outmode``).
Use `jq <https://stedolan.github.io/jq>`_ for pretty-printing. Example using
the test suite data::

    $ cd findsame/tests
    $ findsame data | jq .
    [
      {
        "dir:empty": [
          "data/dir2/empty_dir",
          "data/dir2/empty_dir_copy",
          "data/empty_dir",
          "data/empty_dir_copy"
        ],
        "file:empty": [
          "data/dir2/empty_dir/empty_file",
          "data/dir2/empty_dir_copy/empty_file",
          "data/empty_dir/empty_file",
          "data/empty_dir_copy/empty_file",
          "data/empty_file",
          "data/empty_file_copy"
        ]
      },
      {
        "dir": [
          "data/dir1",
          "data/dir1_copy"
        ]
      },
      {
        "file": [
          "data/file1",
          "data/file1_copy"
        ]
      },
      {
        "file": [
          "data/dir1/file2",
          "data/dir1/file2_copy",
          "data/dir1_copy/file2",
          "data/dir1_copy/file2_copy",
          "data/file2"
        ]
      },
      {
        "file": [
          "data/lena.png",
          "data/lena_copy.png"
        ]
      }
    ]

This is a json array (list) of objects (dictionaries) of same-hash files/dirs.

Note that currently, we skip symlinks.

performance
-----------
By default, we use ``--nthreads`` equal to the number of cores. However, the
most speed is gained by using ``--limit``. Note that this may lead to false
positives, if files are exactly equal in the first ``LIMIT`` bytes.

Use a simple script to verify (assume that the biggest file is < 100 GiB)::

    $ for x in 100K 300K 500K 1M 5M 100G; do echo $x; findsame -l $x /path/to/dir > /tmp/same-$x; done
    $ for y in $(ls -1 /tmp/same-*); do diff -q $y /tmp/same-100G; done 

Yes this is mostly academic since you need to hash a pile of files multipe
times in order to find the fastest but still correct setting. See the TODO file
for details.

tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

benchmarks
----------
You may run the benchmark script to find the best blocksize and number threads
and/or processes for hash calculations on your machine::

    $ cd benchmark
    $ rm -rf files pics *.json*; ./benchmark.py
    $ ./plot.py

This writes test files of various size to ``benchmark/files`` and runs a couple
of benchmarks (runtime ~10 min for all benchmarks). Tune ``maxsize`` in
``benchmark.py`` to have faster tests or disable some benchmark functions.

Bottom line:

* blocksizes below 512 KiB (``--blocksize 512K``) work best for all file sizes
  on most systems, even though the variation to worst timings is at most factor
  1.25 (e.g. 1 vs. 1.25 seconds)
* multithreading (``-t/--nthreads``): up to 2x speedup on dual-core box -- very
  efficient, use NTHREADS = number of cores for good baseline performance
  (problem is mostly IO-bound)
* multiprocessing (``-p/--nprocs``): less efficient speedup, but on some
  systems NPROCS + NTHREADS is even a bit faster than NTHREADS alone, testing
  is mandatory
* we have a linear increase of runtime with filesize, of course

Tested systems:

* Lenovo E330, Samsung 840 Evo SSD, Core i3-3120M (2 cores, 2 threads / core)
* Lenovo X230, Samsung 840 Evo SSD, Core i5-3210M (2 cores, 2 threads / core)

    * best blocksizes = 256K
    * speedups: NPROCS=2: 1.5, NTHREADS=2..3: 1.9,
      no gain when using NPROCS+NTHREADS

* FreeNAS 11 (FreeBSD 11.0), ZFS mirror WD Red WD40EFRX, Intel Celeron J3160
  (4 cores, 1 thread / core)

    * best blocksizes = 80K
    * speedups: NPROCS=3..4: 2.1..2.2, NTHREADS=4..6: 2.6..2.7, NPROCS=3..4,NTHREADS=4: 3

more usage examples
-------------------

Output with hashes (``-o 2``, default is ``-o 1``)::

    $ findsame data -o2 | jq . | head -n20
    {
      "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
        "dir:empty": [
          "data/dir2/empty_dir",
          "data/dir2/empty_dir_copy",
          "data/empty_dir",
          "data/empty_dir_copy"
        ],
        "file:empty": [
          "data/dir2/empty_dir/empty_file",
          "data/dir2/empty_dir_copy/empty_file",
          "data/empty_dir/empty_file",
          "data/empty_dir_copy/empty_file",
          "data/empty_file",
          "data/empty_file_copy"
        ]
      },
      "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
        "dir": [
          "data/dir1",

In this case the output is one json object where all same-hash files/dirs are
found at the same key (hash).

Note that the order of key-value entries in the output from both ``findsame``
and ``jq`` is random.

Post-processing is only limited by your ability to process json (using ``jq``,
Python, ...).

A common task is to find only groups of equal dirs::

    $ findsame data | jq '.[]|select(.dir)|.dir'
    [
      "data/dir1",
      "data/dir1_copy"
    ]

This and all other ``jq`` commands work for both outmodes (``-o 1``, ``-o 2``).
Now only the files::

    $ findsame data | jq '.[]|select(.file)|.file'
    [
      "data/dir1/file2",
      "data/dir1/file2_copy",
      "data/dir1_copy/file2",
      "data/dir1_copy/file2_copy",
      "data/file2"
    ]
    [
      "data/lena.png",
      "data/lena_copy.png"
    ]
    [
      "data/file1",
      "data/file1_copy"
    ]

Another task is to find the first or *all but* the first elements in a group of
same-hash files/dirs.

Find first element::

    $ findsame data | jq '.[]|.[]|[.[0]]'
    [
      "data/lena.png"
    ]
    [
      "data/dir2/empty_dir"
    ]
    [
      "data/dir2/empty_dir/empty_file"
    ]
    [
      "data/dir1/file2"
    ]
    [
      "data/file1"
    ]
    [
      "data/dir1"
    ]

or w/o the length-1 list::

    $ findsame data | jq '.[]|.[]|.[0]'
    "data/dir2/empty_dir"
    "data/dir2/empty_dir/empty_file"
    "data/dir1/file2"
    "data/lena.png"
    "data/file1"
    "data/dir1"


All but first::

    $ findsame data | jq '.[]|.[]|.[1:]'
    [
      "data/dir1_copy"
    ]
    [
      "data/lena_copy.png"
    ]
    [
      "data/dir1/file2_copy",
      "data/dir1_copy/file2",
      "data/dir1_copy/file2_copy",
      "data/file2"
    ]
    [
      "data/dir2/empty_dir_copy/empty_file",
      "data/empty_dir/empty_file",
      "data/empty_dir_copy/empty_file",
      "data/empty_file",
      "data/empty_file_copy"
    ]
    [
      "data/dir2/empty_dir_copy",
      "data/empty_dir",
      "data/empty_dir_copy"
    ]
    [
      "data/file1_copy"
    ]

And w/o lists::

    $ findsame data | jq '.[]|.[]|.[1:]|.[]'
    "data/file1_copy"
    "data/dir1/file2_copy"
    "data/dir1_copy/file2"
    "data/dir1_copy/file2_copy"
    "data/file2"
    "data/lena_copy.png"
    "data/dir2/empty_dir_copy/empty_file"
    "data/empty_dir/empty_file"
    "data/empty_dir_copy/empty_file"
    "data/empty_file"
    "data/empty_file_copy"
    "data/dir2/empty_dir_copy"
    "data/empty_dir"
    "data/empty_dir_copy"
    "data/dir1_copy"

The last one can be used, for example, to delete all but the first in a group
of equal files/dirs, e.g.::

    $ findsame data | jq '.[]|.[]|.[1:]|.[]' | xargs cp -rvt duplicates/


other tools
-----------
* ``fdupes``
* ``findup`` from ``fslint``

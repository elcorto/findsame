findsame
========

Find duplicate files and directories.

As other tools we use file hashes but additionally, we report duplicate
directories as well, using a Merkle tree for directory hash calculation.

usage
-----

::

    $ ./bin/findsame -h
    usage: findsame [-h] [-b BLOCKSIZE] [-p NPROCS] [-t NTHREADS]
                 file/dir [file/dir ...]

    Find same files and dirs based on file hashes.

    positional arguments:
      file/dir              files and/or dirs to compare

    optional arguments:
      -h, --help            show this help message and exit
      -b BLOCKSIZE, --blocksize BLOCKSIZE
                            read-in blocksize in hash calculation, use units K,M,G
                            as in 100M, 218K or just 1024 (bytes) [256.0K]
      -p NPROCS, --nprocs NPROCS
                            number of parallel processes
      -t NTHREADS, --nthreads NTHREADS
                            threads per process

The output format is json::

    {
        hash1: {
            dir/file: [
                name1,
                name2,
                ...
            ]
        hash2: {
            ...
            },
        ...
    }

Use `jq <https://stedolan.github.io/jq>`_ for pretty-printing. Example using
the test suite data::

    $ cd findsame/tests
    $ findsame data | jq .
    {
      "0a96c2e755258bd46abdde729f8ee97d234dd04e": {
        "file": [
          "data/lena.png",
          "data/lena_copy.png"
        ]
      },
      "312382290f4f71e7fb7f00449fb529fce3b8ec95": {
        "file": [
          "data/file1",
          "data/file1_copy"
        ]
      },
      "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
        "dir": [
          "data/dir1",
          "data/dir1_copy"
        ]
      },
      "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
        "file:empty": [
          "data/dir2/empty_dir/empty_file",
          "data/dir2/empty_dir_copy/empty_file",
          "data/empty_dir/empty_file",
          "data/empty_dir_copy/empty_file",
          "data/empty_file",
          "data/empty_file_copy"
        ],
        "dir:empty": [
          "data/dir2/empty_dir",
          "data/dir2/empty_dir_copy",
          "data/empty_dir",
          "data/empty_dir_copy"
        ]
      },
      "9619a9b308cdebee40f6cef018fef0f4d0de2939": {
        "file": [
          "data/dir1/file2",
          "data/dir1/file2_copy",
          "data/dir1_copy/file2",
          "data/dir1_copy/file2_copy",
          "data/file2"
        ]
      }
    }


Note that the order of key-value entries in the output from both
``findsame`` and ``jq`` is random.

Post-processing is only limited by your ability to process json (using ``jq``,
Python, ...).

A common task is to find only groups of equal dirs::

    $ findsame data | jq '.[]|select(.dir)|.dir'
    [
      "data/dir1",
      "data/dir1_copy"
    ]

Or only the files::

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

tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

benchmarks
----------
We like performance, that's why we have a pretty extensive benchmark suite.
You may run the benchmark script to find the best blocksize and number threads
and/or processes for hash calculations on your machine::

    $ cd benchmark
    $ rm -rf files pics results.json; ./benchmark.py
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

other tools
-----------
* ``fdupes``
* ``fdindup`` from ``fslint``

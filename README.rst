About
=====

Find duplicate files and directories.

As other tools we use file hashes but additionally, we report duplicate
directories as well, using a Merkle tree for directory hash calculation.

To increase performance, we use parallel hash calculation and optional limits
on to-be-hashed data.


Install
=======

From pypi:

.. code-block:: shell

    $ pip3 install findsame

Dev install of this repo:

.. code-block:: shell

    $ git clone ...
    $ cd findsame
    $ pip3 install -e .

The core part (package ``findsame`` and the CLI ``bin/findsame``) has no
external dependencies. If you want to run the benchmarks (see "Benchmarks"
below), install:

.. code-block:: shell

    $ pip3 install -r requirements_benchmark.txt


Usage
=====

::

    usage: findsame [-h] [-b BLOCKSIZE] [-l LIMIT] [-L AUTO_LIMIT_MIN] [-p NPROCS]
                    [-t NTHREADS] [-o OUTMODE] [-v]
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
                            read limit (bytes or 'auto'), if bytes then same units
                            as for BLOCKSIZE apply, calculate hash only over the
                            first LIMIT bytes, makes things go faster for may
                            large files, try 500K [default: None], use 'auto' to
                            try to determine the smallest value necessary
                            automatically
      -L AUTO_LIMIT_MIN, --auto-limit-min AUTO_LIMIT_MIN
                            start value for auto LIMIT calculation when --limit
                            auto is used [default: 8.0K]
      -p NPROCS, --nprocs NPROCS
                            number of parallel processes [default: 1]
      -t NTHREADS, --nthreads NTHREADS
                            threads per process [default: 4]
      -o OUTMODE, --outmode OUTMODE
                            1: list of dicts (values of dict from mode 2), one
                            dict per hash, 2: dict of dicts (full result), keys
                            are hashes, 3: compact, sort by type (file, dir)
                            [default: 3]
      -v, --verbose         enable verbose/debugging output

The output format is json, see ``-o/--outmode``, default is ``-o 3``. An
example using the test suite data:

.. code-block:: shell

    $ cd findsame/tests
    $ findsame data | jq .
    {
      "dir:empty": [
        [
          "data/dir2/empty_dir",
          "data/dir2/empty_dir_copy",
          "data/empty_dir",
          "data/empty_dir_copy"
        ]
      ],
      "dir": [
        [
          "data/dir1",
          "data/dir1_copy"
        ]
      ],
      "file:empty": [
        [
          "data/dir2/empty_dir/empty_file",
          "data/dir2/empty_dir_copy/empty_file",
          "data/empty_dir/empty_file",
          "data/empty_dir_copy/empty_file",
          "data/empty_file",
          "data/empty_file_copy"
        ]
      ],
      "file": [
        [
          "data/dir1/file2",
          "data/dir1/file2_copy",
          "data/dir1_copy/file2",
          "data/dir1_copy/file2_copy",
          "data/file2"
        ],
        [
          "data/lena.png",
          "data/lena_copy.png"
        ],
        [
          "data/file1",
          "data/file1_copy"
        ]
      ]
    }

This returns a dict whose keys are the path type (file, dir). Values are nested
lists. Each sub-list contains paths having the same hash. A special case is
``file:empty`` and ``dir:empty`` which actually have the same hash (that of an
empty string), which is not visible in this format. Use ``-o1`` or ``-o2`` in
that case. More examples below.

Use `jq <https://stedolan.github.io/jq>`_ for pretty-printing. Post-processing
is only limited by your ability to process json (using ``jq``, Python, ...).

Note that the order of key-value entries in the output from both ``findsame``
and ``jq`` is random.

Note that currently, we skip symlinks.


Performance
===========

Parallel hash calculation
-------------------------
By default, we use ``--nthreads`` equal to the number of cores. See
"Benchmarks" below.

Limit data to be hashed
-----------------------

Static limit
~~~~~~~~~~~~
Apart from parallelization, by far the most speed is gained by using
``--limit``. Note that this may lead to false positives, if files are exactly
equal in the first ``LIMIT`` bytes. Finding a good enough value can be done by
trial and error. Try 500K. This is still quite fast and seems to cover most
real-world data.

Automatic optimal limit
~~~~~~~~~~~~~~~~~~~~~~~
We have an *experimental* feature where we iteratively increase ``LIMIT`` to
find the smallest possible value. In every iteration, we increase the last
limit by multiplying with ``config.cfg.auto_limit_increase_fac``, with that
re-calculate only the hash of files that have the same hash as others within
the last ``LIMIT`` and check whether their new hashes are now different. This
works but hasn't been extensively benchmarked. The assumption is that a small
number of iterations on a subset of all files (those reported equal so far)
converges quickly and is still faster than a non-optimal ``LIMIT`` or even no
limit at all when you have many big files (as in GiB).

Related options and defaults:

* ``--limit auto``
* ``--auto-limit-min 8K`` = ``config.cfg.auto_limit_min``
* ``config.cfg.auto_limit_increase_fac=2`` (no cmd line so far)

Observations so far:

Convergence corner cases: When files are equal in a good chunk at file start
and ``auto_limit_min`` is small, then the first few iterations show no change
in files being equal (which we use to detect converged limit values). To
circumvent early converge here, we iterate until the number of equal files
changes. The worst case scenario is that ``auto_limit_min`` is already optimal.
Since there is no way to determine that a priori, we will iterate until limit
hits the biggest file size, which may be slow. That is why it is important to
choose ``auto_limit_min`` small enough.

``auto_limit_min``: Don't use very small values such as 20 (that is 20 bytes).
We found that this can converge to a local optimum (converged but too many
equal files reported), depending in the structure of the headers of the files
you compare. Stick with something like a small multiple of the blocksize of
your file system (we use 8K).


Tests
=====

Run ``nosetests3`` (maybe ``apt install python3-nose`` before (Debian)).


Benchmarks
==========

You may run the benchmark script to find the best blocksize and number threads
and/or processes for hash calculations on your machine.

.. code-block:: shell

    $ cd findsame/benchmark
    $ ./clean.sh
    $ ./benchmark.py
    $ ./plot.py

This writes test files of various size to ``benchmark/files`` and runs a couple
of benchmarks (runtime ~10 min for all benchmarks). Make sure to avoid doing
any other extensive IO tasks while the benchmarks run, of course.

**The default value of "maxsize" in benchmark.py (in the __main__ part) is only
some MiB to allow quick testing. This needs to be changed to, say, 1 GiB in
order to have meaningful benchmarks.**

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


Output modes
============

Default (``-o3``)
-----------------

The default output format is ``-o3`` (same as the initial example above).

.. code-block:: shell

    $ findsame -o3 data | jq .
    {
      "dir:empty": [
        [
          "data/dir2/empty_dir",
          "data/dir2/empty_dir_copy",
          "data/empty_dir",
          "data/empty_dir_copy"
        ]
      ],
      "dir": [
        [
          "data/dir1",
          "data/dir1_copy"
        ]
      ],
      "file:empty": [
        [
          "data/dir2/empty_dir/empty_file",
          "data/dir2/empty_dir_copy/empty_file",
          "data/empty_dir/empty_file",
          "data/empty_dir_copy/empty_file",
          "data/empty_file",
          "data/empty_file_copy"
        ]
      ],
      "file": [
        [
          "data/dir1/file2",
          "data/dir1/file2_copy",
          "data/dir1_copy/file2",
          "data/dir1_copy/file2_copy",
          "data/file2"
        ],
        [
          "data/lena.png",
          "data/lena_copy.png"
        ],
        [
          "data/file1",
          "data/file1_copy"
        ]
      ]
    }


Output with hashes (``-o2``)
-----------------------------

.. code-block:: shell

    $ findsame -o2 data | jq .
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
          "data/dir1_copy"
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
      },
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
      }
    }

The output is one dict (json object) where all same-hash files/dirs are found
at the same key (hash).

Dict values (``-o1``)
---------------------
The format ``-o1`` lists only the dict values from ``-o2``, i.e. a list of
dicts.

.. code-block:: shell

    $ findsame -o1 data | jq .
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


More usage examples
===================

Here we show examples of common post-processing tasks using ``jq``. When the
``jq`` command works for all three output modes, we don't specify the ``-o``
option.

Count the total number of all equals:

.. code-block:: shell

    $ findsame data | jq '.[]|.[]|.[]' | wc -l

Find only groups of equal dirs:

.. code-block:: shell

    $ findsame -o1 data | jq '.[]|select(.dir)|.dir'
    $ findsame -o2 data | jq '.[]|select(.dir)|.dir'
    $ findsame -o3 data | jq '.dir|.[]'
    [
      "data/dir1",
      "data/dir1_copy"
    ]

Groups of equal files:

.. code-block:: shell

    $ findsame -o1 data | jq '.[]|select(.file)|.file'
    $ findsame -o2 data | jq '.[]|select(.file)|.file'
    $ findsame -o3 data | jq '.file|.[]'
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

Find the first element in a group of equal items (file or dir):

.. code-block:: shell

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

or more compact w/o the length-1 list:

.. code-block:: shell

    $ findsame data | jq '.[]|.[]|.[0]'
    "data/dir2/empty_dir"
    "data/dir2/empty_dir/empty_file"
    "data/dir1/file2"
    "data/lena.png"
    "data/file1"
    "data/dir1"


Find *all but the first* element in a group of equal items (file or dir):

.. code-block:: shell

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

And more compact:

.. code-block:: shell

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

The last one can be used to remove all but the first in a group of equal
files/dirs:

.. code-block:: shell

    $ findsame data | jq '.[]|.[]|.[1:]|.[]' | xargs cp -rvt duplicates/

``jq`` trick: preserve color in ``less(1)``:

.. code-block:: shell

   $ findsame data | jq . -C | less -R


Other tools
===========

* ``fdupes``
* ``findup`` from ``fslint``

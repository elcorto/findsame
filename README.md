About
=====

Find duplicate files and directories.

As other tools we use file hashes but additionally, we report duplicate
directories as well, using a Merkle tree for directory hash calculation.

To increase performance, we use

* parallel hash calculation (`-t/--nthreads` option), see Benchmarks below
* optional limits on data to be hashed (`-l/--limit` option)

Install
=======

From pypi:

```sh
    $ pip install findsame
```

Dev install of this repo:

```sh
    $ git clone ...
    $ cd findsame
    $ pip install -e .
```

The core part (package `findsame` and the CLI `bin/findsame`) has no
external dependencies. If you want to run the benchmarks (see
"Benchmarks" below), install:

```sh
    $ pip install -r requirements_benchmark.txt
```

Usage
=====

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
                            100M, 256K or just 1024 (bytes), if LIMIT is used and
                            BLOCKSIZE < LIMIT then we require mod(LIMIT,
                            BLOCKSIZE) = 0 else we set BLOCKSIZE = LIMIT [default:
                            256.0K]
      -l LIMIT, --limit LIMIT
                            read limit (bytes, see also BLOCKSIZE), calculate hash
                            only over the first LIMIT bytes, makes things go
                            faster for may large files, try 512K [default: None]
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

The output format is json, see `-o/--outmode`, default is `-o 3`. An
example using the test suite data:

```sh
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
```

This returns a dict whose keys are the path type (file, dir). Values are
nested lists. Each sub-list contains paths having the same hash. Note that we
also report empty files and dirs.

Use [jq](https://stedolan.github.io/jq) for pretty-printing, e.g.

```sh
    $ findsame data | jq .

    # keep colors in less(1)
    $ findsame data | jq . -C | less -R
```

To check out large amounts of data (as in GiB) for the first time, use the
`-l/--limit` option for speed and use `less -n` as well (don't wait for input
to load)

```sh
    $ findsame -l512K data | jq . -C | less -nR
```
Post-processing is only limited by your ability to process json (using
`jq`, Python, ...).

Note that the order of key-value entries in the output from both
`findsame` and `jq` is random.

Note that currently, we skip symlinks.

Performance
===========

Parallel hash calculation
-------------------------

By default, we use `--nthreads` equal to the number of cores. See
"Benchmarks" below.

Limit data to be hashed
-----------------------

Apart from parallelization, by far the most speed is gained by using
`--limit`. Note that this may lead to false positives, if files are
exactly equal in the first `LIMIT` bytes. Finding a good enough value
can be done by trial and error. Try 512K. This is still quite fast and
seems to cover most real-world data.

Tests
=====

Run `nosetests`, `pytest` or any other test runner with test discovery.

Benchmarks
==========

You may run the benchmark script to find the best blocksize and number
threads and/or processes for hash calculations on your machine.

```sh
    $ cd findsame/benchmark
    $ ./clean.sh
    $ ./benchmark.py
    $ ./plot.py
```

This writes test files of various size to `benchmark/files` and runs a
couple of benchmarks (runtime \~10 min for all benchmarks). Make sure to
avoid doing any other extensive IO tasks while the benchmarks run, of
course.

**The default value of "maxsize" in benchmark.py (in the `__main__`
part) is only some MiB to allow quick testing. This needs to be changed
to, say, 1 GiB in order to have meaningful benchmarks.**

Observations:

* blocksizes below 512 KiB (`-b/--blocksize 512K`) work best for all file
  sizes on most systems, even though the variation to worst timings is
  at most factor 1.25 (e.g. 1 vs. 1.25 seconds)
* multithreading (`-t/--nthreads`): up to 2x speedup on dual-core box
  -- very efficient, use NTHREADS = number of cores for good baseline
  performance (problem is mostly IO-bound)
* multiprocessing (`-p/--nprocs`): less efficient speedup, but on some
  systems NPROCS + NTHREADS is even a bit faster than NTHREADS alone,
  testing is mandatory
* we have a linear increase of runtime with filesize, of course

Output modes
============

Default (`-o3`)
---------------

The default output format is `-o3` (same as the initial example above).

```sh
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
```

Output with hashes (`-o2`)
--------------------------

```sh
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
```

The output is one dict (json object) where all same-hash files/dirs are
found at the same key (hash).

Dict values (`-o1`)
-------------------

The format `-o1` lists only the dict values from `-o2`, i.e. a list of
dicts.

```sh
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
```

More usage examples
===================

Here we show examples of common post-processing tasks using `jq`. When
the `jq` command works for all three output modes, we don't specify the
`-o` option.

Count the total number of all equals:

```sh
    $ findsame data | jq '.[]|.[]|.[]' | wc -l
```

Find only groups of equal dirs:

```sh
    $ findsame -o1 data | jq '.[]|select(.dir)|.dir'
    $ findsame -o2 data | jq '.[]|select(.dir)|.dir'
    $ findsame -o3 data | jq '.dir|.[]'
    [
      "data/dir1",
      "data/dir1_copy"
    ]
```

Groups of equal files:

```sh
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
```

Find the first element in a group of equal items (file or dir):

```sh
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
```

or more compact w/o the length-1 list:

```sh
    $ findsame data | jq '.[]|.[]|.[0]'
    "data/dir2/empty_dir"
    "data/dir2/empty_dir/empty_file"
    "data/dir1/file2"
    "data/lena.png"
    "data/file1"
    "data/dir1"
```

Find *all but the first* element in a group of equal items (file or
dir):

```sh
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
```

And more compact:

```sh
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
```

The last one can be used to remove all but the first in a group of equal
files/dirs:

```sh
    $ findsame data | jq '.[]|.[]|.[1:]|.[]' | xargs cp -rvt duplicates/
```

Other tools
===========

`fdupes`, `jdupes`, `duff`, `rdfind`, `rmlint`, `findup` (from `fslint`)

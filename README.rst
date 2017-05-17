findsame
========

Find duplicate files and directories.

As other tools we use file hashes but additionally, we report duplicate
directories as well, using a Merkle tree for directory hash calculation.

usage
-----

::

	$ ./fs.py -h
	usage: fs.py [-h] [-n NCORES] [-b BLOCKSIZE] file/dir [file/dir ...]

	Find same files and dirs based on file hashes.

	positional arguments:
	  file/dir              files and/or dirs to compare

	optional arguments:
	  -h, --help            show this help message and exit
	  -n NCORES, --ncores NCORES
							number of processes for parallel hash calc in Merkle
							tree
	  -b BLOCKSIZE, --blocksize BLOCKSIZE
							read-in blocksize in hash calculation, use units K,M,G
							as in 100M, 218K or just 1024 (bytes) [256.0K]

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

	$ ./fs.py test/data | jq .
	{
	  "0a96c2e755258bd46abdde729f8ee97d234dd04e": {
		"file": [
		  "test/data/lena.png",
		  "test/data/lena_copy.png"
		]
	  },
	  "312382290f4f71e7fb7f00449fb529fce3b8ec95": {
		"file": [
		  "test/data/file1",
		  "test/data/file1_copy"
		]
	  },
	  "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
		"dir": [
		  "test/data/dir1",
		  "test/data/dir1_copy"
		]
	  },
	  "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
		"file:empty": [
		  "test/data/dir2/empty_dir/empty_file",
		  "test/data/dir2/empty_dir_copy/empty_file",
		  "test/data/empty_dir/empty_file",
		  "test/data/empty_dir_copy/empty_file",
		  "test/data/empty_file",
		  "test/data/empty_file_copy"
		],
		"dir:empty": [
		  "test/data/dir2/empty_dir",
		  "test/data/dir2/empty_dir_copy",
		  "test/data/empty_dir",
		  "test/data/empty_dir_copy"
		]
	  },
	  "9619a9b308cdebee40f6cef018fef0f4d0de2939": {
		"file": [
		  "test/data/dir1/file2",
		  "test/data/dir1/file2_copy",
		  "test/data/dir1_copy/file2",
		  "test/data/dir1_copy/file2_copy",
		  "test/data/file2"
		]
	  }
	}


Note that the order of key-value entries in the output from both
``fs.py`` and ``jq`` is random.

Post-processing is only limited by your ability to process json (using ``jq``,
Python, ...).

A common task is to find only groups of equal dirs::

	$ ./fs.py test/data | jq '.[]|select(.dir)|.dir'
	[
	  "test/data/dir1",
	  "test/data/dir1_copy"
	]

Or only the files::

	$ ./fs.py test/data | jq '.[]|select(.file)|.file'
	[
	  "test/data/dir1/file2",
	  "test/data/dir1/file2_copy",
	  "test/data/dir1_copy/file2",
	  "test/data/dir1_copy/file2_copy",
	  "test/data/file2"
	]
	[
	  "test/data/lena.png",
	  "test/data/lena_copy.png"
	]
	[
	  "test/data/file1",
	  "test/data/file1_copy"
	]

Another task is to find the first or *all but* the first elements in a group of
same-hash files/dirs.

Find first element::

	$ ./fs.py test/data | jq '.[]|.[]|[.[0]]'
	[
	  "test/data/lena.png"
	]
	[
	  "test/data/dir2/empty_dir"
	]
	[
	  "test/data/dir2/empty_dir/empty_file"
	]
	[
	  "test/data/dir1/file2"
	]
	[
	  "test/data/file1"
	]
	[
	  "test/data/dir1"
	]

or w/o the length-1 list::

	$ ./fs.py test/data | jq '.[]|.[]|.[0]'
	"test/data/dir2/empty_dir"
	"test/data/dir2/empty_dir/empty_file"
	"test/data/dir1/file2"
	"test/data/lena.png"
	"test/data/file1"
	"test/data/dir1"


All but first::

	$ ./fs.py test/data | jq '.[]|.[]|.[1:]'
	[
	  "test/data/dir1_copy"
	]
	[
	  "test/data/lena_copy.png"
	]
	[
	  "test/data/dir1/file2_copy",
	  "test/data/dir1_copy/file2",
	  "test/data/dir1_copy/file2_copy",
	  "test/data/file2"
	]
	[
	  "test/data/dir2/empty_dir_copy/empty_file",
	  "test/data/empty_dir/empty_file",
	  "test/data/empty_dir_copy/empty_file",
	  "test/data/empty_file",
	  "test/data/empty_file_copy"
	]
	[
	  "test/data/dir2/empty_dir_copy",
	  "test/data/empty_dir",
	  "test/data/empty_dir_copy"
	]
	[
	  "test/data/file1_copy"
	]


tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

benchmarks
----------
You may run the benchmark script to find the best blocksize and number of cores
for hash calculations::

    $ cd benchmark
    $ rm -rf files results.json; ./benchmark.py

This writes test files of various size to ``benchmark/files`` and runs a coulpe
of benchmarks (runs < 5 min).

Bottom line:

* blocksizes around 256 KiB (``--blocksize 256K``) work best for all file
  sizes, even though the variation to worst timings is at most factor 1.25
  (e.g. 1 vs. 1.25 seconds)
* using multiple worker threads helps, up to 2x speedup, multiprocessing shows
  slowdown instead
* we have a linear increase of runtime with filesize, of course

Tested systems:

* Lenovo E330, Samsung 840 Evo SSD, Core i3-3120M (2 cores, 2 threads / core)
* Lenovo X230, Samsung 840 Evo SSD, Core i5-3210M (2 cores, 2 threads / core)
* FreeBSD NAS, ZFS mirror, Intel Celeron J3160 (4 cores, 1 thread / core)



other tools
-----------
* ``fdupes``
* ``fdindup`` from ``fslint``

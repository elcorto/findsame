findsame
========

Find duplicate files and directories.

As other tools we use file hashes but additionally, we report duplicate
directories as well, using a Merkle tree for directory hash calculation.

usage
-----

::

    $ ./findsame.py -h
    usage: findsame.py [-h] [-v] [-n NCORES] [-b BLOCKSIZE]
                       file/dir [file/dir ...]

    Find same files and dirs based on file hashes.

    positional arguments:
      file/dir              files and/or dirs to compare

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose         verbose
      -n NCORES, --ncores NCORES
                            number of processes for parallel hash calc in Merkle
                            tree
      -b BLOCKSIZE, --blocksize BLOCKSIZE
                            read-in blocksize (byte) in hash calculation [1048576]

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

	$ ./findsame.py test/data | jq .
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
``findsame.py`` and ``jq`` is random.

Post-processing is only limited by your ability to process json (using ``jq``,
Python, ...). In case of equal files/dirs, a common task is to find the first
or *all but* the first elements in a group of same-hash files/dirs.

Find first element::

	$ ./findsame.py test/data | jq 'map_values(map_values([.[0]]))'
	{
	  "9619a9b308cdebee40f6cef018fef0f4d0de2939": {
		"file": [
		  "test/data/dir1/file2"
		]
	  },
	  "0a96c2e755258bd46abdde729f8ee97d234dd04e": {
		"file": [
		  "test/data/lena.png"
		]
	  },
	  "312382290f4f71e7fb7f00449fb529fce3b8ec95": {
		"file": [
		  "test/data/file1"
		]
	  },
	  "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
		"file:empty": [
		  "test/data/dir2/empty_dir/empty_file"
		],
		"dir:empty": [
		  "test/data/dir2/empty_dir"
		]
	  },
	  "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
		"dir": [
		  "test/data/dir1"
		]
	  }
	}

or ``jq 'map_values(map_values(.[0]))'`` if you don't want a length-one list.

Only the values::

	$ ./findsame.py test/data | jq '.[]|.[]|.[0]'
	"test/data/dir1"
	"test/data/lena.png"
	"test/data/file1"
	"test/data/dir1/file2"
	"test/data/dir2/empty_dir/empty_file"
	"test/data/dir2/empty_dir"

Test if we got the same::

	$ ./findsame.py test/data | jq 'map_values(map_values(.[0]))|.[]|.[]' | sort > aa
	$ ./findsame.py test/data | jq '.[]|.[]|.[0]' | sort > bb
	$ diff aa bb

All but first::

	$ ./findsame.py test/data | jq 'map_values(map_values(.[1:]))'
	{
	  "312382290f4f71e7fb7f00449fb529fce3b8ec95": {
		"file": [
		  "test/data/file1_copy"
		]
	  },
	  "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
		"dir": [
		  "test/data/dir1_copy"
		]
	  },
	  "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
		"dir:empty": [
		  "test/data/dir2/empty_dir_copy",
		  "test/data/empty_dir",
		  "test/data/empty_dir_copy"
		],
		"file:empty": [
		  "test/data/dir2/empty_dir_copy/empty_file",
		  "test/data/empty_dir/empty_file",
		  "test/data/empty_dir_copy/empty_file",
		  "test/data/empty_file",
		  "test/data/empty_file_copy"
		]
	  },
	  "0a96c2e755258bd46abdde729f8ee97d234dd04e": {
		"file": [
		  "test/data/lena_copy.png"
		]
	  },
	  "9619a9b308cdebee40f6cef018fef0f4d0de2939": {
		"file": [
		  "test/data/dir1/file2_copy",
		  "test/data/dir1_copy/file2",
		  "test/data/dir1_copy/file2_copy",
		  "test/data/file2"
		]
	  }
	}

Values::

	$ ./findsame.py test/data | jq '.[]|.[]|.[1:]|.[]'
	"test/data/dir2/empty_dir_copy"
	"test/data/empty_dir"
	"test/data/empty_dir_copy"
	"test/data/dir2/empty_dir_copy/empty_file"
	"test/data/empty_dir/empty_file"
	"test/data/empty_dir_copy/empty_file"
	"test/data/empty_file"
	"test/data/empty_file_copy"
	"test/data/dir1_copy"
	"test/data/lena_copy.png"
	"test/data/file1_copy"
	"test/data/dir1/file2_copy"
	"test/data/dir1_copy/file2"
	"test/data/dir1_copy/file2_copy"
	"test/data/file2"

Test if we produce the same output::

	$ ./findsame.py test/data | jq 'map_values(map_values(.[1:]))|.[]|.[]|.[]' | sort > aa
	$ ./findsame.py test/data | jq '.[]|.[]|.[1:]|.[]' | sort > bb
	$ diff aa bb

tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

benchmarks
----------
You may run the benchmark script to find the best blocksize and number of cores
for hash calculations::

    $ cd benchmark
    $ rm -rf files results.json; ./benchmark.py

This writes test files of various size to ``benchmark/files``. Tune
``collection_size`` in ``benchmark.main()`` for more and bigger test files.
A collection is a number of files whose total size is ``collection_size``.
Default is 100 MiB, i.e. files from 1 x 100MiB to 800 x 128 kiB files.

Bottom line (test system: Lenovo E330, Samsung 840 Evo SSD, Core i3-3120M)

* blocksizes around 512 kiB (``--blocksize 524288``) work best for all file
  sizes, even though the variation to worst timings is at most factor 1.25
  (e.g. 1 vs. 1.25 seconds)
* using multiple cores actually slows things down since the hashing seems to be
  IO-bound (reading is slower than hashing blocks)
* there is a strong (up to factor 2) and non-monotonic dependence on file size,
  may be related to disk cache size (runtime keeps increasing until certain
  characteristic file sizes and then drops) .. not fully investigated yet

other tools
-----------
* ``fdupes``
* ``fdindup`` from ``fslint``

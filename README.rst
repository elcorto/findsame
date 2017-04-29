findsame
========

Find duplicate files and directories. As other tools such as ``fdupes`` or
``fslint``'s ``fdindup`` (see ``/usr/share/fslint/fslint/findup``), we also use
simple file hashes.

But additionally, we report duplicate directories as well, using a
Merkle tree for directory hash calculation.

example
-------

The default output format is json, where::

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
	  "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
		"dir": [
		  "test/data/dir1",
		  "test/data/dir1_copy"
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
	  },
	  "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
		"dir:empty": [
		  "test/data/dir2/empty_dir",
		  "test/data/dir2/empty_dir_copy",
		  "test/data/empty_dir",
		  "test/data/empty_dir_copy"
		],
		"file:empty": [
		  "test/data/empty_file",
		  "test/data/empty_file_copy"
		]
	  },
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
	  }
	}

Post-processing is only limited by your ability to process json (using ``jq``,
Python, ...). In case of equal files/dirs, a common task is to
find the first or *all but* the first elements in a group of same-hash files/dirs.

Find first element::

	$ ./findsame.py test/data | jq 'map_values(map_values(.[0]))'
	{
	  "0a96c2e755258bd46abdde729f8ee97d234dd04e": {
		"file": "test/data/lena.png"
	  },
	  "9619a9b308cdebee40f6cef018fef0f4d0de2939": {
		"file": "test/data/dir1/file2"
	  },
	  "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
		"file:empty": "test/data/empty_file",
		"dir:empty": "test/data/dir2/empty_dir"
	  },
	  "312382290f4f71e7fb7f00449fb529fce3b8ec95": {
		"file": "test/data/file1"
	  },
	  "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
		"dir": "test/data/dir1"
	  }
	}

All but first::

	$ ./findsame.py test/data | jq 'map_values(map_values(.[1:]))'
	{
	  "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
		"dir:empty": [
		  "test/data/dir2/empty_dir_copy",
		  "test/data/empty_dir",
		  "test/data/empty_dir_copy"
		],
		"file:empty": [
		  "test/data/empty_file_copy"
		]
	  },
	  "9619a9b308cdebee40f6cef018fef0f4d0de2939": {
		"file": [
		  "test/data/dir1/file2_copy",
		  "test/data/dir1_copy/file2",
		  "test/data/dir1_copy/file2_copy",
		  "test/data/file2"
		]
	  },
	  "0a96c2e755258bd46abdde729f8ee97d234dd04e": {
		"file": [
		  "test/data/lena_copy.png"
		]
	  },
	  "55341fe74a3497b53438f9b724b3e8cdaf728edc": {
		"dir": [
		  "test/data/dir1_copy"
		]
	  },
	  "312382290f4f71e7fb7f00449fb529fce3b8ec95": {
		"file": [
		  "test/data/file1_copy"
		]
	  }
	}


tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

benchmarks
----------
You may run the benchmark suite to find the best blocksize and number of cores
for hash calculations::

    $ cd benchmark
    $ ./benchmark.py /path/to/tmpdir
    $ ./plot.py /path/to/tmpdir

This writes test files of various size to ``/path/to/tmpdir``. Tune
``collection_size`` in ``benchmark.py`` for more and bigger test files.

Bottom line:

* blocksizes around 512 kiB (``--blocksize 524288``) work best for all file
  sizes, even though the variation to worst timings is at most factor 1.25
  (e.g. 1 vs. 1.25 seconds)
* don't use multiple cores as this actually slows things down since the hashing
  seems to be IO-bound (reading is slower than hashing blocks)
* there is a strong dependence on file size (up to factor 2), may be related to
  disk cache size (runtime keeps increasing until certain characteristic file
  sizes and then drops) .. not fully investigated yet

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


There is also the old 'simple' format, where each file/dir is prefixed with
its hash::

    $ ./findsame.py -f simple test/data/
    da39a3ee5e6b4b0d3255bfef95601890afd80709 dir:empty: test/data/dir2/empty_dir
    da39a3ee5e6b4b0d3255bfef95601890afd80709 dir:empty: test/data/dir2/empty_dir_copy
    da39a3ee5e6b4b0d3255bfef95601890afd80709 dir:empty: test/data/empty_dir
    da39a3ee5e6b4b0d3255bfef95601890afd80709 dir:empty: test/data/empty_dir_copy
    55341fe74a3497b53438f9b724b3e8cdaf728edc dir: test/data/dir1
    55341fe74a3497b53438f9b724b3e8cdaf728edc dir: test/data/dir1_copy
    9619a9b308cdebee40f6cef018fef0f4d0de2939 file: test/data/dir1/file2
    9619a9b308cdebee40f6cef018fef0f4d0de2939 file: test/data/dir1/file2_copy
    9619a9b308cdebee40f6cef018fef0f4d0de2939 file: test/data/dir1_copy/file2
    9619a9b308cdebee40f6cef018fef0f4d0de2939 file: test/data/dir1_copy/file2_copy
    9619a9b308cdebee40f6cef018fef0f4d0de2939 file: test/data/file2
    312382290f4f71e7fb7f00449fb529fce3b8ec95 file: test/data/file1
    312382290f4f71e7fb7f00449fb529fce3b8ec95 file: test/data/file1_copy
    0a96c2e755258bd46abdde729f8ee97d234dd04e file: test/data/lena.png
    0a96c2e755258bd46abdde729f8ee97d234dd04e file: test/data/lena_copy.png
    da39a3ee5e6b4b0d3255bfef95601890afd80709 file:empty: test/data/empty_file
    da39a3ee5e6b4b0d3255bfef95601890afd80709 file:empty: test/data/empty_file_copy

Some post-processing similar to the ``jq`` examples above. Grep the first entry
in a group of equal files (all same hash). 5 lines out of 17 in this example::

    $ findsame.py ... > same
    $ wc -l same
    17 same

    $ first=$(awk '{print $1}' same | sort -u | xargs -l -IX grep X -m1 same)
    $ echo $first
    0a96c2e755258bd46abdde729f8ee97d234dd04e file: /home/elcorto/soft/git/findsame/test/data/lena.png
    312382290f4f71e7fb7f00449fb529fce3b8ec95 file: /home/elcorto/soft/git/findsame/test/data/file1
    55341fe74a3497b53438f9b724b3e8cdaf728edc dir: /home/elcorto/soft/git/findsame/test/data/dir1
    9619a9b308cdebee40f6cef018fef0f4d0de2939 file: /home/elcorto/soft/git/findsame/test/data/dir1/file2
    da39a3ee5e6b4b0d3255bfef95601890afd80709 dir:empty: /home/elcorto/soft/git/findsame/test/data/dir2/empty_dir

Now find all *but* the first one (useful for deleting all but one equal file per
group): make a regex from the names in ``$first`` and use ``grep -v`` to
invert. Make sure we match to the line end by adding whitespace (``[ ]*$``) in order
to distinghuish ``test/data/dir1`` and ``test/data/dir1/file2`` when grepping::

    $ rest=$(echo $first | awk '{printf $3"[ ]*$\n"}' | paste -s -d'|')
    $ echo $rest
    test/data/lena.png[ ]*$|test/data/file1[ ]*$|test/data/dir1[ ]*$|test/data/dir1/file2[ ]*$|test/data/dir2/empty_dir[ ]*$
    $ grep -vE $rest same | wc -l
    12

tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

findsame
========

Small tool to find duplicate files in directories. As other tools such as
``fdupes`` or ``fslint``'s ``fdindup`` (see
``/usr/share/fslint/fslint/findup``), we also use simple file hashes. 

But additionally, we report duplicate directories as well.

example
-------

::

	$ ./findsame.py test/data/
	dir:empty: test/data/dir2/empty_dir_copy
	dir:empty: test/data/empty_dir
	dir:empty: test/data/dir2/empty_dir
	dir:empty: test/data/empty_dir_copy

	dir: test/data/dir1_copy
	dir: test/data/dir1

	file: test/data/dir1_copy/file2_copy
	file: test/data/dir1/file2
	file: test/data/file2
	file: test/data/dir1/file2_copy
	file: test/data/dir1_copy/file2

	file:empty: test/data/empty_file
	file:empty: test/data/empty_file_copy

	file: test/data/file1
	file: test/data/file1_copy

tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

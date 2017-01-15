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

tests
-----
Run ``nosetests3`` (maybe ``apt-get install python3-nose`` before (Debian)).

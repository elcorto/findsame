import subprocess
import os
from findsame import findsame as fs
from numpy import sort
pj = os.path.join


def hash_file_subprocess(fn):
    return subprocess.getoutput(r"sha1sum {} | cut -d ' ' -f1".format(fn))


def test_hash():
    fn = pj(os.path.dirname(__file__), 'data/lena.png')
    assert fs.hash_file(fn) == hash_file_subprocess(fn)


def test_subpath():
    assert fs.is_subpath('a/b', 'a')
    assert fs.is_subpath('a/b/', 'a')
    assert fs.is_subpath('a/b', 'a/')
    assert fs.is_subpath('a/b/', 'a/')
    assert fs.is_subpath('/a/b', '/a/')
    assert fs.is_subpath('/a/b/', '/a/')
    
    assert not fs.is_subpath('a', 'a')
    assert not fs.is_subpath('/a', '/a')
    assert not fs.is_subpath('a/', 'a/')
    assert not fs.is_subpath('/a/', '/a/')


def test_exe_stdout():
    here = os.path.dirname(__file__)
    exe = '{}/../findsame.py'.format(here)
    out = subprocess.check_output('{} test/data'.format(exe), shell=True)
    with open('{}/ref_output'.format(here)) as fd:
        ref = sort(fd.read().splitlines()).tolist()
    val = sort(out.decode().splitlines()).tolist()
    assert val == ref, "val:\n{}\nref:\n{}".format(val, ref)

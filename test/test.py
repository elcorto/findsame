import subprocess, os, json
from findsame import findsame as fs
from numpy import sort
pj = os.path.join


#-------------------------------------------------------------------------------
# helpers
#-------------------------------------------------------------------------------

def dict_equal(aa, bb):
    if set(aa.keys()) != set(bb.keys()):
        return False
    for akey, aval in aa.items():
        if isinstance(aval, dict):
            if not dict_equal(aval, bb[akey]):
                return False
        else:
            if not aval == bb[akey]:
                return False
    return True


def hash_file_subprocess(fn):
    return subprocess.getoutput(r"sha1sum {} | cut -d ' ' -f1".format(fn))


#-------------------------------------------------------------------------------
# tests
#-------------------------------------------------------------------------------

def test_dict_equal():
    aa = {'a':1, 'b': {'b': 2}}
    bb = {'a':1, 'b': {'b': 2}}
    assert dict_equal(aa, bb) 
    aa = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    bb = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    assert dict_equal(aa, bb) 
    
    aa = {'a':1, 'b': {'b': 2}}
    bb = {'a':1, 'b': {'b': 3}}
    assert not dict_equal(aa, bb) 
    assert not dict_equal(bb, aa) 
    aa = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    bb = {'a':1, 'b': {'b': 2}, 'c': [3,2,1]}
    assert not dict_equal(aa, bb) 
    assert not dict_equal(bb, aa) 

    aa = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    bb = {'a':1, 'b': {'b': 2}}
    assert not dict_equal(aa, bb) 
    assert not dict_equal(bb, aa) 

    aa = {'b': {'b': 2}}
    bb = {'a':1, 'b': {'b': 2}}
    assert not dict_equal(aa, bb) 
    assert not dict_equal(bb, aa) 


def test_hash():
    fn = pj(os.path.dirname(__file__), 'data/lena.png')
    assert fs.hash_file(fn) == hash_file_subprocess(fn)


def _preproc_simple(out, ref_fn):
    _mangle = lambda x: sort(x.splitlines()).tolist()
    with open(ref_fn) as fd:
        ref = _mangle(fd.read())
    val = _mangle(out)
    return val, ref


def _preproc_json(val, ref_fn):
    val = json.loads(val)
    with open(ref_fn) as fd:
        ref = json.load(fd)
    return val, ref


def test_exe_stdout():
    here = os.path.dirname(__file__)
    for fmt, preproc_func in [('json', _preproc_json), ('simple', _preproc_simple)]:
        exe = '{here}/../findsame.py -f {fmt}'.format(here=here, fmt=fmt)
        for args in ['test/data', 'test/data/*']:
            out = subprocess.check_output('{} {}'.format(exe, args), shell=True)
            out = out.decode()
            ref_fn = '{here}/ref_output_{fmt}'.format(here=here, fmt=fmt)
            val, ref = preproc_func(out, ref_fn) 
            assert val == ref, "val:\n{}\nref:\n{}".format(val, ref)

import subprocess, os, json, random
from findsame.lib import calc
from findsame.lib import common as co
from numpy import sort
pj = os.path.join


#-------------------------------------------------------------------------------
# helpers
#-------------------------------------------------------------------------------

def hash_file_subprocess(fn):
    return subprocess.getoutput(r"sha1sum {} | cut -d ' ' -f1".format(fn))


#-------------------------------------------------------------------------------
# tests
#-------------------------------------------------------------------------------

def test_dict_equal():
    aa = {'a':1, 'b': {'b': 2}}
    bb = {'a':1, 'b': {'b': 2}}
    assert co.dict_equal(aa, bb) 
    aa = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    bb = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    assert co.dict_equal(aa, bb) 
    
    aa = {'a':1, 'b': {'b': 2}}
    bb = {'a':1, 'b': {'b': 3}}
    assert not co.dict_equal(aa, bb) 
    assert not co.dict_equal(bb, aa) 
    aa = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    bb = {'a':1, 'b': {'b': 2}, 'c': [3,2,1]}
    assert not co.dict_equal(aa, bb) 
    assert not co.dict_equal(bb, aa) 

    aa = {'a':1, 'b': {'b': 2}, 'c': [1,2,3]}
    bb = {'a':1, 'b': {'b': 2}}
    assert not co.dict_equal(aa, bb) 
    assert not co.dict_equal(bb, aa) 

    aa = {'b': {'b': 2}}
    bb = {'a':1, 'b': {'b': 2}}
    assert not co.dict_equal(aa, bb) 
    assert not co.dict_equal(bb, aa) 


def test_hash():
    fn = pj(os.path.dirname(__file__), 'data/lena.png')
    assert calc.hash_file(fn) == hash_file_subprocess(fn)


def _preproc_json(val, ref_fn):
    val = json.loads(val)
    with open(ref_fn) as fd:
        ref = json.load(fd)
    return val, ref, lambda x,y: co.dict_equal(x, y)


def test_exe_stdout():
    here = os.path.dirname(__file__)
    for opts in ['', '-v', '-n 2', '-b 512K']:
        for fmt, preproc_func in [('json', _preproc_json)]:
            exe = '{here}/../fs.py {opts} 2>/dev/null'.format(here=here, opts=opts)
            for args in ['test/data', 'test/data/*']:
                out = subprocess.check_output('{} {}'.format(exe, args), shell=True)
                out = out.decode()
                print(out)
                ref_fn = '{here}/ref_output_{fmt}'.format(here=here, fmt=fmt)
                val, ref, comp = preproc_func(out, ref_fn)
                assert comp(val, ref), "val:\n{}\nref:\n{}".format(val, ref) 

def test_size_str():
    sizes = [1023, random.randint(1000, 300000000000)]
    for sep in ['', ' ', '___']:
        for size in sizes:
            assert co.str2size(co.size2str(size, prec=30)) == size

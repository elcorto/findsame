import subprocess, os, json, random, sys
from findsame import calc
from findsame import common as co
pj = os.path.join


here = os.path.abspath(os.path.dirname(__file__))

#-------------------------------------------------------------------------------
# helpers
#-------------------------------------------------------------------------------

def hash_file_subprocess(fn):
    if sys.platform == 'linux':
        cmd = r"sha1sum {} | cut -d ' ' -f1"
    else:
        # assume BSD-ish system, don't test for
        # sys.platform='freebsd10' or 'darwin' expicitly
        cmd = r"sha1 {} | cut -d= -f2 | tr -d ' '"
    return subprocess.getoutput(cmd.format(fn))


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


def test_hash_file():
    fn = pj(os.path.dirname(__file__), 'data/lena.png')
    assert calc.hash_file(fn) == hash_file_subprocess(fn)

def test_hash_file_limit():
    fn = pj(os.path.dirname(__file__), 'data/lena.png')
    ref = hash_file_subprocess(fn)
    val = calc.hash_file_limit(fn, limit=os.stat(fn).st_size)
    assert val == ref
    val = calc.hash_file_limit(fn, limit=os.stat(fn).st_size - 1)
    assert val != ref

def _preproc_json_verbose(val, ref_fn):
    val = json.loads(val)
    with open(ref_fn) as fd:
        ref = json.load(fd)
    return val, ref, lambda x,y: co.dict_equal(x, y)

def _preproc_json(val, ref_fn):
    val = json.loads(val)
    with open(ref_fn) as fd:
        ref = json.load(fd)
    return val, ref, lambda x,y: x == y

def test_exe_stdout():
    preproc_func = _preproc_json
    cases = [('json_verbose', '-v', _preproc_json_verbose, ''), 
             ('json', '', _preproc_json, '| jq sort'),
             ]
    for name, outer_opts, preproc_func, post in cases:
        # test all combos only once which are not related to output formatting
        if name == 'json_verbose':
            opts_lst = ['', '-p 2', '-t 2', '-p2 -t2', '-b 512K', '-l 128K']
        else:
            opts_lst = ['']
        for opts in opts_lst:
            exe = '{here}/../../bin/findsame {outer_opts} ' \
                  '{opts}'.format(here=here, 
                                  opts=opts,
                                  outer_opts=outer_opts)
            for args in ['data', 'data/*']:
                cmd = '{exe} {here}/{args} 2>&1 | ' \
                      'grep -v SKIP {post}'.format(exe=exe, args=args,
                                                   here=here, post=post)
                print(cmd)
                out = subprocess.check_output(cmd, shell=True)
                out = out.decode()
                out = out.replace(here + '/','')
                print(out)
                ref_fn = '{here}/ref_output_{name}'.format(here=here, name=name)
                val, ref, comp = preproc_func(out, ref_fn)
                assert comp(val, ref), "val:\n{}\nref:\n{}".format(val, ref)

def test_size_str():
    sizes = [1023, random.randint(1000, 300000000000)]
    for size in sizes:
        assert co.str2size(co.size2str(size, prec=30)) == size


def test_lazy():
    class Foo:
        def __init__(self):
            pass
        
        def _get_prop(self):
            return 'prop'

        @co.lazyprop
        def prop(self):
            return self._get_prop()
    
    foo = Foo()
    assert foo.prop == 'prop'
    foo.prop = None
    assert foo.prop is None
    # force re-evaluation 
    del foo.prop
    assert foo.prop == 'prop'
    # assign random value, _get_prop() is not called
    val = 37847128
    foo.prop = val
    assert foo.prop == val

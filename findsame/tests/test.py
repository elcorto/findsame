import subprocess, os, json, random, sys, hashlib
from findsame import calc
from findsame import common as co
from findsame import config
pj = os.path.join
cfg = config.getcfg()


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
    assert calc.hash_file(fn) == hash_file_subprocess(fn) \
        == '0a96c2e755258bd46abdde729f8ee97d234dd04e'


def test_adjust_blocksize():
    limit = 5 
    for blocksize in [1,2,3,4]:
        assert calc.adjust_blocksize(blocksize, limit) == 1
    for blocksize in [5,6,7]:
        assert calc.adjust_blocksize(blocksize, limit) == 5


def test_hash_file_limit():
    bs = cfg.blocksize
    file_200_a = pj(os.path.dirname(__file__), 'data/file_200_a')
    file_200_a_200_b = pj(os.path.dirname(__file__), 'data/file_200_a_200_b')
    hashes = {file_200_a: 'e61cfffe0d9195a525fc6cf06ca2d77119c24a40',
              file_200_a_200_b: 'c29d2522ff37716a8aed11cec28555dd583d8497'}
    assert hashes[file_200_a] == calc.hash_file(file_200_a) == \
        hashlib.sha1(b'a'*200).hexdigest()
    assert hashes[file_200_a_200_b] == calc.hash_file(file_200_a_200_b) == \
        hashlib.sha1(b'a'*200 + b'b'*200).hexdigest()
    for bs in [10, 33, 199, 200, 201, 433, 500]:
        for fn,hsh in hashes.items():
            assert calc.hash_file(fn, blocksize=bs) == hsh
            for limit in [400, 401, 433, 600]:
                assert calc.hash_file_limit(fn, blocksize=bs, limit=limit) == hsh
            assert calc.hash_file_limit(fn, blocksize=bs, limit=200) == \
                    hashes[file_200_a]
    for limit in [1,33,199,200]:
        assert calc.hash_file_limit(file_200_a_200_b, limit=limit, blocksize=bs) == \
                calc.hash_file_limit(file_200_a, limit=limit, blocksize=bs) == \
                calc.hash_file_limit(file_200_a_200_b, limit=limit, blocksize=bs) == \
                hashlib.sha1(b'a'*limit).hexdigest()
        

def _preproc_json_with_hash(val, ref_fn):
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
    cases = [('json_with_hash', '-o2', _preproc_json_with_hash, ''), 
             ('json', '-o1', _preproc_json, '| jq sort'),
             ('json', '', _preproc_json, '| jq sort'),
             ]
    for name, outer_opts, preproc_func, post in cases:
        # test all combos only once which are not related to output formatting
        if name == 'json_with_hash':
            opts_lst = ['', '-p 2', '-t 2', '-p2 -t2', '-b 512K', '-l 128K', 
                        '-b 99K -l 500K']
        else:
            opts_lst = ['']
        for opts in opts_lst:
            exe = '{here}/../../bin/findsame {outer_opts} ' \
                  '{opts}'.format(here=here, 
                                  opts=opts,
                                  outer_opts=outer_opts)
            for args in ['data', 'data/*']:
                cmd = '{exe} {here}/{args} {post}'.format(exe=exe, args=args,
                                                          here=here, post=post)
                print(cmd)
                out = subprocess.check_output(cmd, shell=True)
                out = out.decode()
                out = out.replace(here + '/','')
                print(out)
                ref_fn = '{here}/ref_output_{name}'.format(here=here, name=name)
                val, ref, comp = preproc_func(out, ref_fn)
                assert comp(val, ref), "val:\n{}\nref:\n{}".format(val, ref)


def test_jq():
    jq_cmd_lst = ["jq '.[]|select(.dir)|.dir'",
                  "jq '.[]|select(.file)|.file'",
                  "jq '.[]|.[]|[.[0]]'",
                  "jq '.[]|.[]|.[0]'",
                  "jq '.[]|.[]|.[1:]'",
                  "jq '.[]|.[]|.[1:]|.[]'",
                  ]
    data = pj(os.path.dirname(__file__), 'data')
    for jq_cmd in jq_cmd_lst:
        res = []
        for outopt in ['-o1', '-o2']:
            cmd = '{here}/../../bin/findsame {data} {outopt} ' \
                  '| {jq_cmd}'.format(here=here, 
                                      data=data,
                                      outopt=outopt,
                                      jq_cmd=jq_cmd)
            print(cmd)
            out = subprocess.check_output(cmd, shell=True)
            out = out.decode()
            out = out.replace(here + '/','')
            print(out)
            res.append(out)
        assert res[0] ==  res[1]


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

import subprocess, os, json, random, sys, hashlib
from findsame import calc
from findsame import common as co
from findsame.config import cfg
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
    file_200_a = pj(os.path.dirname(__file__), 'data/limit/deep/files/file_200_a')
    file_200_a_200_b = pj(os.path.dirname(__file__), 'data/limit/deep/files/file_200_a_200_b')
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
                val = calc.hash_file_limit(fn,
                                           blocksize=bs,
                                           limit=limit)
                assert val == hsh, "failed: val={} hsh={} bs={} limit={}".format(
                    val, hsh, bs, limit)
            assert calc.hash_file_limit(fn, blocksize=bs, limit=200) == \
                    hashes[file_200_a]
    for limit in [1,33,199,200]:
        assert calc.hash_file_limit(file_200_a_200_b, limit=limit, blocksize=bs) == \
                calc.hash_file_limit(file_200_a, limit=limit, blocksize=bs) == \
                calc.hash_file_limit(file_200_a_200_b, limit=limit, blocksize=bs) == \
                hashlib.sha1(b'a'*limit).hexdigest()

def _cmp_o3(val, ref):
    if set(val.keys()) != set(ref.keys()):
        print("dict keys not equal")
        return False
    # key = file, dir, file:empty, dir:empty
    # val_lst = [[file1, file2, ...],
    #            [...],
    #            ...]
    # The sub-lists in val_lst (and ref_lst=ref[key]) can be in random order,
    # as is the order of the paths within each list. It is only important that
    # all same-hash paths are present in their sub-list. Therefore we loop over
    # lists, compare sets and count the number of matches.
    for key,val_lst in val.items():
        nsub = len(val_lst)
        if len(ref[key]) != nsub:
            print("not same number of sub-lists")
            return False
        cnt = 0
        for val_sub_lst in val_lst:
            for ref_sub_lst in ref[key]:
                if set(ref_sub_lst) == set(val_sub_lst):
                    cnt += 1
        if cnt != nsub:
            print(f"not exactly {cnt} equal sub-lists")
            return False
    return True


def _preproc_json_o2(val, ref_fn):
    val = json.loads(val)
    with open(ref_fn) as fd:
        ref = json.load(fd)
    return val, ref, lambda x,y: co.dict_equal(x, y)


def _preproc_json_o1(val, ref_fn):
    val = json.loads(val)
    with open(ref_fn) as fd:
        ref = json.load(fd)
    return val, ref, lambda x,y: x == y


def _preproc_json_o3(val, ref_fn):
    val = json.loads(val)
    with open(ref_fn) as fd:
        ref = json.load(fd)
    return val, ref, _cmp_o3


def test_cli():
    cases = [('json_o2', '-o2', _preproc_json_o2, ''),
             ('json_o1', '-o1', _preproc_json_o1, '| jq sort'),
             ('json_o3', '-o3', _preproc_json_o3, ''),
             ]
    for name, outer_opts, preproc_func, post in cases:
        # Test all combos only once which are not related to output formatting.
        # json_o2: the hashes are the ones of the while file, so all limit (-l)
        # values must be bigger than the biggest file.
        #
        # without hashes: We have test data file_200_a, file_200_a_200_b,
        # file_200_a_2000_b which are equal in the first 200 bytes, We test auto
        # limit iteration with -L 10: 10,20,40,80,160,320,640 -> limit=320
        # bytes will be the smallest limit where we start to see that the files
        # are different. A second iteration with doubled limit is performed and
        # if the number of same elements (now 0, before 2) doesn't change
        # (still 0), we are converged.
        if name == 'json_o2':
            opts_lst = ['', '-p 2', '-t 2', '-p2 -t2', '-b 512K', '-l 128K',
                        '-b 99K -l 500K']
        else:
            opts_lst = ['-l auto', '-l auto -L 8K', '-l auto -L 10']
        for opts in opts_lst:
            exe = f'{here}/../../bin/findsame {outer_opts} {opts}'
            for args in ['data', 'data/*']:
                cmd = f'{exe} {here}/{args} {post}'
                print(cmd)
                out = subprocess.check_output(cmd, shell=True)
                out = out.decode()
                out = out.replace(here + '/','')
                print(out)
                ref_fn = f'{here}/ref_output_{name}'
                val, ref, comp = preproc_func(out, ref_fn)
                assert comp(val, ref), f"{name}\nval:\n{val}\nref:\n{ref}"


def test_auto_limit_cli():
    # This is already covered in test_cli() since the result is [] and
    # thus doesn't show up in canned reference results, but we test it
    # explicitely here anyway .. because we can!
    opts = "-l auto -L 10 -o1"
    cmd = f'{here}/../../bin/findsame {opts} {here}/data/limit/deep/files/file_200_a*'
    out = subprocess.check_output(cmd, shell=True).decode().strip()
    assert out == '[]'


def test_auto_limit_cli_debug_iter():
    opts = "-l auto -L 50 -v"
    cmd = f"{here}/../../bin/findsame {opts} {here}/data | \
             grep -E 'DBG.+auto_limit:.+(#same|limit=)'"
    out = subprocess.check_output(cmd, shell=True).decode().strip()
    with open(f"{here}/ref_output_debug_auto_limit") as fd:
        ref = fd.read().strip()
    assert out == ref

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


def test_walk_files():
    d = pj(os.path.dirname(__file__), 'data')
    # all files in test data, includes links, note that
    #   os.path.isfile(<a link>)
    # is True !
    x = [pj(r,f) for r,_,fs in os.walk(d) for f in fs]
    assert len(x) > 0
    for fn in x:
        assert os.path.exists(fn)
        assert os.path.isfile(fn)
    sx2 = set()
    for r,_,fs in calc.FileDirTree.walk_files(x):
        for f in fs:
            fn = pj(r,f)
            sx2.add(fn)
            assert os.path.exists(fn)
            assert os.path.isfile(fn)
    sx = set(x)
    assert sx == sx2, sx - sx2

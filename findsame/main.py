import functools, os
from findsame import common as co
from findsame import calc

def main(files_dirs, nprocs=1, nthreads=1, blocksize=None):
    file_hashes = dict()
    dir_hashes = dict()
    for path in files_dirs:
        # skipping links
        if os.path.isfile(path):
            file_hashes[path] = calc.hash_file(path, blocksize)
        elif os.path.isdir(path):
            tree = calc.MerkleTree(path, calc=True, nprocs=nprocs,
                                   nthreads=nthreads, blocksize=blocksize)
            file_hashes.update(tree.file_hashes)
            dir_hashes.update(tree.dir_hashes)
        else:
            co.debug_msg("SKIP: {}".format(path))

    file_store = co.invert_dict(file_hashes)
    dir_store = co.invert_dict(dir_hashes)

    # result:
    #     {hashA: {typX: [path1, path2],
    #              typY: [path3]},
    #      hashB: {typX: [...]},
    #      ...}
    result = dict()
    empty = calc.hashsum('')
    for kind, dct in [('dir', dir_store), ('file', file_store)]:
        for hsh, paths in dct.items():
            hsh_dct = result.get(hsh, {})
            if len(paths) > 1:
                # exclude single deep files, where each upper dir has the same
                # hash as the deep file
                #   foo/
                #   foo/bar/
                #   foo/bar/baz
                #   foo/bar/baz/file
                # In that case for kind=='dir':
                #   paths = ['foo', 'foo/bar', 'foo/bar/baz']
                #   lens  = [1,2,3]
                #   diffs = [1,1,1]
                if kind == 'dir':
                    lens = [len(calc.split_path(x)) for x in paths] 
                    diffs = map(lambda x,y: y-x, lens[:-1], lens[1:])
                    if functools.reduce(lambda x,y: x == y == 1, diffs):
                        continue
                if hsh == empty:
                    typ = '{}:empty'.format(kind)
                else:
                    typ = '{}'.format(kind)
                typ_paths = hsh_dct.get(typ, []) + paths
                hsh_dct.update({typ: typ_paths})
                result.update({hsh: hsh_dct})
    return result

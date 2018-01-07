import functools, os
from findsame import common as co
from findsame import calc


def calc_fprs(files_dirs, config):
    file_fprs = dict()
    dir_fprs = dict()
    for path in files_dirs:
        # skipping links
        if os.path.isfile(path):
            file_fprs[path] = calc.hash_file(path, config.blocksize)
        elif os.path.isdir(path):
            tree = calc.MerkleTree(path, calc=True, config=config)
            file_fprs.update(tree.leaf_fprs)
            dir_fprs.update(tree.node_fprs)
        else:
            co.debug_msg("SKIP: {}".format(path))
    
    # leaf_fprs, dir_fprs:
    #   {path1: fprA,
    #    path2: fprA,
    #    path3: fprB,
    #    ...}
    #
    # file_store, dir_store:
    #    fprA: [path1, path2],
    #    fprB: [path3],
    #    ...}
    file_store = co.invert_dict(file_fprs)
    dir_store = co.invert_dict(dir_fprs)
    return file_store, dir_store


def assemble_result(file_store, dir_store):
    # result:
    #   {fprA: {typX: [path1, path2],
    #            typY: [path3]},
    #    fprB: {typX: [...]},
    #    ...}
    result = dict()
    empty = calc.hashsum('')
    for kind, store in [('dir', dir_store), ('file', file_store)]:
        for hsh, paths in store.items():
            hsh_dct = result.get(hsh, {})
            # exclude single items, only multiple fprs for now (hence the
            # name find*same* :)
            if len(paths) > 1:
                # exclude single deep files, where each upper dir has the same
                # fpr as the deep file
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


def main(files_dirs, config):
    """
    Parameters
    ----------
    files_dirs : seq
        list of strings w/ files and/or dirs
    config : config.Config
    """
    return assemble_result(*calc_fprs(files_dirs, config))

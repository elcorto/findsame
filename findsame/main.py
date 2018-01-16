import functools, os
from findsame import common as co
from findsame import calc
from findsame.config import config


def calc_fprs(files_dirs):
    if config.limit:
        file_fpr_func = functools.partial(calc.hash_file_limit_core,
                                          blocksize=config.blocksize,
                                          limit=config.limit)
    else:
        file_fpr_func = functools.partial(calc.hash_file,
                                          blocksize=config.blocksize)
    file_fprs = dict()
    dir_fprs = dict()
    for path in files_dirs:
        # skipping links
        if os.path.isfile(path) and not os.path.islink(path):
            file_fprs[path] = file_fpr_func(path)
        elif os.path.isdir(path):
            tree = calc.MerkleTree(path, calc=True,
                                   leaf_fpr_func=file_fpr_func)
            file_fprs.update(tree.leaf_fprs)
            dir_fprs.update(tree.node_fprs)
        else:
            co.debug_msg("skip link: {}".format(path))
    
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
    if config.outmode == 1:
        return [dct for dct in result.values()]
    elif config.outmode == 2:
        return result
    else:
        raise Exception("illegal value for "
                        "outmode: {}".format(config.outmode))


def main(files_dirs):
    """
    Parameters
    ----------
    files_dirs : seq
        list of strings w/ files and/or dirs
    """
    return assemble_result(*calc_fprs(files_dirs))

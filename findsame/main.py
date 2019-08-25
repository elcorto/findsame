import functools, os
from findsame import common as co
from findsame import calc

def get_tree(files_dirs):
    files = []
    dirs = []
    for path in files_dirs:
        # skip links
        if os.path.islink(path):
            co.debug_msg(f"skip link: {path}")
            continue
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            dirs.append(path)
        else:
            raise Exception(f"unkown file/dir type for: {path}")

    tree = calc.FileDirTree(files=files)
    for dr in dirs:
        dt = calc.FileDirTree(dr=dr)
        tree.update(dt)
    return tree

def get_merkle_tree(files_dirs, cfg):
    return calc.MerkleTree(get_tree(files_dirs), calc=True, cfg=cfg)


def assemble_result(merkle_tree, cfg):
    # result:
    #   {fprA: {typX: [path1, path2],
    #           typY: [path3]},
    #    fprB: {typX: [...]},
    #    ...}
    result = dict()
    empty = calc.hashsum('')
    for kind, inv_fprs in [('dir', merkle_tree.inverse_node_fprs()),
                           ('file', merkle_tree.inverse_leaf_fprs())]:
        for hsh, paths in inv_fprs.items():
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
                    typ = f'{kind}:empty'
                else:
                    typ = f'{kind}'
                typ_paths = hsh_dct.get(typ, []) + paths
                hsh_dct.update({typ: typ_paths})
                result.update({hsh: hsh_dct})
    if cfg.outmode == 1:
        return [dct for dct in result.values()]
    elif cfg.outmode == 2:
        return result
    else:
        raise Exception(f"illegal value for outmode: {cfg.outmode}")


def main(files_dirs, cfg):
    """
    Parameters
    ----------
    files_dirs : seq
        list of strings w/ files and/or dirs
    """
    return assemble_result(get_merkle_tree(files_dirs, cfg), cfg)

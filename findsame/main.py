import functools
from collections import defaultdict
import os

from findsame import common as co
from findsame import calc
from findsame.config import cfg


def get_merkle_tree(files_dirs):
    files = []
    dirs = []
    for path in files_dirs:
        if os.path.exists(path):
            if os.path.isdir(path):
                # loose files w/o connection to each other by a top dir, even if
                # they have, e.g.
                #   findsame dir/file_*
                # instead of
                #   findsame dir
                dirs.append(path)
            else:
                # everything else (files, links, name dpipes, ...), we deal w/ that
                # in FileDirTree
                files.append(path)
        else:
            raise Exception(f"not found: {path}")

    tree = calc.FileDirTree(files=files)
    for dr in dirs:
        dt = calc.FileDirTree(dr=dr)
        tree.update(dt)
    return calc.MerkleTree(tree)


def assemble_result(merkle_tree):
    # result:
    #   {fprA: {typX: [path1, path2],
    #           typY: [path3]},
    #    fprB: {typX: [...]},
    #    ...}
    merkle_tree.calc_fprs()
    if cfg.outmode == 3:
        result = defaultdict(list)
    else:
        result = defaultdict(dict)
    cases = [('dir',
              co.invert_dict(merkle_tree.node_fprs),
              calc.EMPTY_DIR_FPR,
              calc.MISSING_DIR_FPR),
             ('file',
              co.invert_dict(merkle_tree.leaf_fprs),
              calc.EMPTY_FILE_FPR,
              calc.MISSING_FILE_FPR)]
    for kind, inv_fprs, empty_fpr, missing_fpr in cases:
        for fpr, paths in inv_fprs.items():
            # exclude single items, only multiple fprs for now (hence the
            # name find*same* :)
            if fpr == missing_fpr:
                co.debug_msg(f"skip missing {kind}: {paths}")
                continue
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
                if fpr == empty_fpr:
                    typ = f'{kind}:empty'
                else:
                    typ = f'{kind}'
                if cfg.outmode == 3:
                    result[typ].append(paths)
                else:
                    result[fpr][typ] = result[fpr].get(typ, []) + paths
    if cfg.outmode == 1:
        return list(result.values())
    elif cfg.outmode in [2,3]:
        return result
    else:
        raise Exception(f"illegal value for outmode: {cfg.outmode}")


def main(files_dirs):
    """
    Parameters
    ----------
    files_dirs : seq
        list of strings w/ files and/or dirs
    """
    return assemble_result(get_merkle_tree(files_dirs))

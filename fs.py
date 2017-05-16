#!/usr/bin/python3

import functools, argparse, json, os
from findsame.lib import common as co
from findsame.lib import calc

def main(files_dirs, nworkers=None, parallel=None, blocksize=None):
    file_hashes = dict()
    dir_hashes = dict()
    for path in files_dirs:
        # skipping links
        if os.path.isfile(path):
            file_hashes[path] = calc.hash_file(path, blocksize)
        elif os.path.isdir(path):
            tree = calc.MerkleTree(path, calc=True, nworkers=nworkers,
                                   parallel=parallel, blocksize=blocksize)
            file_hashes.update(tree.file_hashes)
            dir_hashes.update(tree.dir_hashes)
        else:
            debug_msg("SKIP: {}".format(path))

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

if __name__ == '__main__':

    desc = "Find same files and dirs based on file hashes."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('files_dirs', nargs='+', metavar='file/dir',
                        help='files and/or dirs to compare', default=[])
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False,
                        help='verbose')
    parser.add_argument('-n', '--nworkers', type=int,
                        default=None,
                        help='number of worker threads for parallel hash calc '
                             'in Merkle tree')
    parser.add_argument('-b', '--blocksize', 
                        default=co.size2str(calc.BLOCKSIZE),
                        help='read-in blocksize in hash calculation, '
                             'use units K,M,G as in 100M, 218K or just '
                             '1024 (bytes) '
                             '[%(default)s]')
    args = parser.parse_args()
    VERBOSE = args.verbose 
    print(json.dumps(main(files_dirs=args.files_dirs, 
                          nworkers=args.nworkers,
                          parallel='threads',
                          blocksize=co.str2size(args.blocksize))))

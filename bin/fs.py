#!/usr/bin/env python3

import argparse, json
from findsame import common as co
from findsame import calc, main

if __name__ == '__main__':

    desc = "Find same files and dirs based on file hashes."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('files_dirs', nargs='+', metavar='file/dir',
                        help='files and/or dirs to compare', default=[])
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
    print(json.dumps(main.main(files_dirs=args.files_dirs, 
                               nworkers=args.nworkers,
                               parallel='threads',
                               blocksize=co.str2size(args.blocksize))))

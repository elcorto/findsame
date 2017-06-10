#!/usr/bin/env python3

import argparse, json
from findsame import common as co
from findsame import calc, main

if __name__ == '__main__':

    desc = "Find same files and dirs based on file hashes."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('files_dirs', nargs='+', metavar='file/dir',
                        help='files and/or dirs to compare', default=[])
    parser.add_argument('-b', '--blocksize', 
                        default=co.size2str(calc.BLOCKSIZE),
                        help='read-in blocksize in hash calculation, '
                             'use units K,M,G as in 100M, 218K or just '
                             '1024 (bytes) '
                             '[%(default)s]')
    parser.add_argument('-p', '--nprocs', 
                        default=1, type=int,
                        help='number of parallel processes')
    parser.add_argument('-t', '--nthreads', 
                        default=1, type=int,
                        help='threads per process')
    args = parser.parse_args()
    print(json.dumps(main.main(files_dirs=args.files_dirs,
                               nprocs=args.nprocs,
                               nthreads=args.nthreads,
                               blocksize=co.str2size(args.blocksize))))

#!/usr/bin/python3

import sys
import timeit
import subprocess

import psweep as ps


def func(pset):
    flush_cmd = "sudo -A sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'"
    exe_cmd = f"{pset['tool_cmd']} {pset['datadir']} > /dev/null"
    if pset['cache'] == 'warm':
        cmd = exe_cmd
    else:
        cmd = f"{flush_cmd}; {exe_cmd}"
    print(f"    {pset['tool_cmd']}")
    times = timeit.repeat(lambda: subprocess.run(cmd, shell=True),
                          number=1,
                          repeat=3)
    return {'timing': min(times)}


if __name__ == '__main__':

    assert len(sys.argv) > 1
    # usage:
    #   ./this.py /path/to/dir_1 [/path/to/dir_2 ...]
    datadirs = sys.argv[1:]

    tool_cmd = ps.plist('tool_cmd', [
        'findsame',
        'findsame -t1',
        'findsame -l 512K',
        'findsame -l 4K',
        'findsame -t1 -l 4K',
        'jdupes -q -r',
        'jdupes -q -rQ',
        'jdupes -q -rTT',
        'duff -ra',
        'duff -rat',
        'rdfind -outputname /dev/null',
        ])

    # cache warming only once per datadir to save time, that's why we need to
    # loop over ps.run() calls instead of going w/ the usual psweep workflow
    # (assemble all params, then call ps.run() once), instead we use one of
    # ps.run()'s features: append to existing db on disk
    for _datadir in datadirs:
        print(_datadir)
        for _cache in ['cold', 'warm']:
            print(f"  {_cache}")
            if _cache == 'warm':
                subprocess.run(f"findsame {_datadir} > /dev/null", shell=True)

            datadir = ps.plist('datadir', [_datadir])
            cache = ps.plist('cache', [_cache])
            params = ps.pgrid(tool_cmd,
                              datadir,
                              cache)

            # results in calc/results.pk
            ps.run(func, params)

#!/usr/bin/python3

import os
import re
import string
from itertools import chain

import numpy as np
from matplotlib import pyplot as plt

from psweep import psweep as ps

from findsame import main, common as co, analyze


class Group:
    """Helper to group commands that do similar stuff."""
    def __init__(self, sym):
        self.sym = sym
        self.xs = []
        self.ys = []
        self.xticklabels = []


def filter_cmd(cmd):
    """Remove some non-technical option strings from `cmd`, which is assumed to
    be a string containing a shell command.
    """
    cmd = cmd.replace(' -outputname /dev/null', '')
    cmd = cmd.replace(' -q', '')
    return cmd


if __name__ == '__main__':

    os.makedirs('pics', exist_ok=True)

    # anonymize dirs for plots which we publish
    anon_dirs = True

    # group commands which perform roughly the same thing together, the last
    # group's commands are unrelated
    cmd_groups = \
        [('s', r"^(findsame|jdupes -rQ|rdfind|duff -ra)$"),
         ('o', r"^(jdupes -r|duff -rat)$"),
         ('^', r"^(findsame -l 4K|jdupes -rTT)$"),
         ('*', r"^findsame.*(-t1|-l 512K).*$"),
         ]

    df = ps.df_read('calc/results.pk')

    letters = iter(string.ascii_uppercase)
    datadirs = [analyze.DataDir(pth, next(letters)) for pth in df.datadir.unique()]
    datadirs.append(analyze.DataDir(os.environ['HOME'], 'HOME'))
    print(datadirs)

    # plot bench data, exclude HOME, for which we only calculate the histogram
    # later
    for datadir in datadirs[:-1]:
        fig,ax = plt.subplots()
        for cache,color in [('cold', 'tab:blue'), ('warm', 'tab:orange')]:
            this_df = df[(df.cache==cache) & (df.datadir==datadir.path)]
            cmds = list(map(filter_cmd, this_df.tool_cmd))
            ix = 0
            groups = []
            for symbol, rex in cmd_groups:
                grp = Group(symbol)
                for ii,cmd in enumerate(cmds):
                    if re.match(rex, cmd):
                        grp.xs.append(ix)
                        grp.ys.append(this_df.timing.values[ii])
                        grp.xticklabels.append(cmd)
                        ix += 1
                groups.append(grp)

            # exclude last group, it is special b/c points are unrelated
            for grp in groups[:-1]:
                line, = ax.plot(grp.xs, grp.ys, grp.sym + '--', lw=2, ms=10,
                                color=color)

            # label on the last line, once per color
            line.set_label(f"cache {cache}")

            # plot last group
            grp = groups[-1]
            ax.plot(grp.xs, grp.ys, grp.sym, lw=2, ms=10,
                    color=color)

        # use last group list for ticks, all group lists must have the same
        # tickabels
        ax.set_xticks(list(chain(*(g.xs for g in groups))))
        ax.set_xticklabels(list(chain(*(g.xticklabels for g in groups))),
                           ha='right')

        dirname = datadir.alias if anon_dirs else datadir.path
        ax.set_title(f"dir: {dirname}  {datadir.size_str}")
        ax.legend(markerscale=0)
        ax.set_ylabel("time (s)")

        for tl in ax.get_xticklabels():
            tl.set_rotation(45)
        fig.subplots_adjust(bottom=0.25)
        fig.savefig(f"pics/bench_dir_{datadir.alias}.png")

    # histograms
    if anon_dirs:
        labels = [dd.alias for dd in datadirs]
    else:
        labels = [dd.path for dd in datadirs]

    fig,ax = analyze.hist([dd.sizes for dd in datadirs],
                          bins=50,
                          labels=labels)
    ax.set_xlabel('filesize')
    fig.savefig(f"pics/hist.png")

    plt.show()

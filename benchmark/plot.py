#!/usr/bin/python3

import sys, os
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np


def plot(study, df, xprop, yprop, cprop, plot='plot'):
    fig,ax = plt.subplots()
    df = df[df['study'] == study]
    df = df.sort_values(xprop)
    xticks = []
    xticklabels = []
    for const in np.sort(df[cprop].unique()):
        msk = df[cprop] == const
        label = df[msk][cprop].values[0]
        x = df[msk][xprop] / 1024**2
        y = df[msk][yprop]
        getattr(ax, plot)(x, y, 'o-', label=label)
        if len(x) > len(xticks):
            xticks = x
            xprop_str = xprop + '_str'
            sel = xprop_str if xprop_str in df[msk].columns else xprop
            xticklabels = df[msk][sel]

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels, rotation=45)
##    ax.set_xlabel(xprop + ' (MiB)')
    ax.set_xlabel(xprop)
    ax.set_ylabel(yprop)
    fig.subplots_adjust(bottom=0.2)
    ax.legend(title=cprop.replace('_str',''))


if __name__ == '__main__':
    tmpdir = sys.argv[1]
    df = pd.io.json.read_json(os.path.join(tmpdir, 'results.json'))
    
    plot('blocksize', df, 'blocksize', 'timing', 'filesize_str', plot='semilogx')
    plot('filesize', df, 'filesize', 'timing', 'blocksize_str')
    plot('collection', df, 'ncores', 'timing', 'blocksize_str')

    plt.show()

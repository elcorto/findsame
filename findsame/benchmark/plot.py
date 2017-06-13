#!/usr/bin/env python3

import os
import pandas as pd
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np


def plot(study, df, xprop, yprop, cprop=None, plot='plot'):
    df = df.sort_values(xprop)
    df = df[df['study'] == study]
    if cprop is None:
        cprop = 'study'
        const_itr = [study]
    else:
        const_itr = df[cprop].unique()
    fig,ax = plt.subplots()
    xticks = []
    xticklabels = []
    for const in const_itr:
        msk = df[cprop] == const
        label = df[msk][cprop].values[0]
        x = df[msk][xprop]
        y = df[msk][yprop]
        getattr(ax, plot)(x, y, 'o-', label=label)
        if len(x) > len(xticks):
            xticks = x
            xprop_str = xprop + '_str'
            sel = xprop_str if xprop_str in df[msk].columns else xprop
            xticklabels = df[msk][sel]
    
    ylabel = 'timing (s)' if yprop == 'timing' else yprop
    rotation = 45 if xprop.endswith('size') else None
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels, rotation=rotation)
    ax.set_xlabel(xprop)
    ax.set_ylabel(ylabel)
    ax.set_title(study)
    fig.subplots_adjust(bottom=0.2)
    ax.legend(title=cprop.replace('_str',''))
    os.makedirs('pics', exist_ok=True)
    savefig(fig, study)


def savefig(fig, study):
    for ext in ['pdf', 'png']:
        fig.savefig("pics/{study}.{ext}".format(study=study, ext=ext), dpi=300)


if __name__ == '__main__':
    df = pd.io.json.read_json('results.json', orient='split')

    plot('main_blocksize_single', df, 'blocksize', 'timing', 'filesize_str', plot='semilogx')
    plot('main_filesize_single', df, 'filesize', 'timing', 'blocksize_str')
    plot('main_blocksize', df, 'blocksize', 'timing', plot='semilogx')

    plot('main_parallel', df, 'nworkers', 'timing', 'pool_type')
    plot('hash_file_parallel', df, 'nworkers', 'timing', 'pool_type')
    
    # call this last since it modifies `df` globally
    study = 'main_parallel_2d'
    if study in df.study.values:
        df = df[df['study'] == study]
        xx = df.nprocs.values
        yy = df.nthreads.values
        zz = df.timing.values
        x = np.unique(xx)
        y = np.unique(yy)
        X,Y = np.meshgrid(x, y, indexing='ij');
        Z = zz.reshape((len(x),len(y))).T
        fig, ax = plt.subplots(subplot_kw=dict(projection='3d'))
        ax.set_xlabel('procs')
        ax.set_ylabel('threads') 
        ax.plot_wireframe(X,Y,Z)
        ax.scatter(xx, yy, zz)
        savefig(fig, study)

    plt.show()

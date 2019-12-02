#!/usr/bin/env python3

import os, sys, collections, itertools, functools

import numpy as np

from matplotlib import pyplot as plt
# for projection='3d'
from mpl_toolkits.mplot3d import Axes3D

from psweep import psweep as ps


def to_seq(arg):
    if isinstance(arg, collections.abc.Sequence) and not isinstance(arg, str):
        return arg
    else:
        return [arg]


def plot(study, df, xprop, yprop, const_prop=None, plot='plot'):
    const_prop = to_seq(const_prop) if const_prop is not None else None
    if study in df.study.values:
        df = df.sort_values(xprop)
        df = df[df['study'] == study]
        if const_prop is None:
            const_prop = ['study']
            const_params = [{'study': study}]
        else:
            # const_prop = ['pool_type', 'share_leafs']
            # const_vals = [('thread', True),
            #               ('thread', False),
            #               ('proc', True),
            #               ('proc', False)]
            # const_params =
            #   [{'pool_type': 'thread', 'share_leafs': True},
            #    {'pool_type': 'thread', 'share_leafs': False},
            #    {'pool_type': 'proc', 'share_leafs': True},
            #    {'pool_type': 'proc', 'share_leafs': False}]
            const_vals = itertools.product(*(df[c].unique() for c in const_prop))
            const_params = (dict(zip(const_prop, cv)) for cv in const_vals)
        fig,ax = plt.subplots()
        xticks = []
        xticklabels = []
        for const_pset in const_params:
            msk = functools.reduce(np.logical_and,
                                   ((df[kk]==vv) for kk,vv in const_pset.items()))
            label = ','.join("{}={}".format(kk,vv) for kk,vv in const_pset.items())
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
        fig.subplots_adjust(bottom=0.2)
        ax.legend()
        tmp = np.unique(df.maxsize_str.values)
        assert len(tmp) == 1
        maxsize_str = tmp[0]
        ax.set_title('{} maxsize={}'.format(study, maxsize_str))
        savefig(fig, '{}_{}'.format(study, maxsize_str))


def savefig(fig, name):
    os.makedirs('pics', exist_ok=True)
##    for ext in ['pdf', 'png']:
    for ext in ['png']:
        fig.savefig("pics/{name}.{ext}".format(name=name, ext=ext), dpi=300)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        results = sys.argv[1]
    else:
        results = 'results.json'
    dfall = ps.df_read(results, fmt='json')
    if 'share_leafs' in dfall.columns:
        dfall.share_leafs = dfall.share_leafs.astype(bool)
    for maxsize_str in np.unique(dfall.maxsize_str.values):
        df = dfall[dfall.maxsize_str == maxsize_str]
        if 'main_blocksize_single' in df.study.values:
            plot('main_blocksize_single', df, 'blocksize', 'timing', 'filesize_str', plot='semilogx')
        if 'main_filesize_single' in df.study.values:
            plot('main_filesize_single', df, 'filesize', 'timing', 'blocksize_str')
        if 'main_blocksize' in df.study.values:
            plot('main_blocksize', df, 'blocksize', 'timing', plot='semilogx')
        if 'main_parallel' in df.study.values:
            plot('main_parallel', df, 'nworkers', 'timing', ['pool_type', 'share_leafs'])
        if 'hash_file_parallel' in df.study.values:
            plot('hash_file_parallel', df, 'nworkers', 'timing', 'pool_type')

        study = 'main_parallel_2d'
        title = '{} maxsize={}'.format(study, maxsize_str)
        if study in df.study.values:
            fig, ax = plt.subplots(subplot_kw=dict(projection='3d'))
            df2d = df[df['study'] == study]
            xx = df2d.nprocs.values
            yy = df2d.nthreads.values
            zz = df2d.timing.values
            x = np.unique(xx)
            y = np.unique(yy)
            X,Y = np.meshgrid(x, y, indexing='ij')
            Z = zz.reshape((len(x),len(y))).T
            min_idx = np.unravel_index(np.argmin(Z), Z.shape)
            min_idx_proc = Z[:,0].argmin()
            min_idx_thread = Z[0,:].argmin()
            xmin = X[min_idx]
            ymin = Y[min_idx]
            zmin = Z[min_idx]
            xmin_proc = x[min_idx_proc]
            ymin_proc = 1
            zmin_proc = Z[min_idx_proc,0]
            xmin_thread = 1
            ymin_thread = y[min_idx_thread]
            zmin_thread = Z[0,min_idx_thread]
            print(title)
            print("global min: nproc={:.0f} nthread={:.0f}, speedup (max/min): {:.1f}".format(x[min_idx[0]], y[min_idx[1]], Z.max()/zmin))
            print("proc   min: {:.0f},                 speedup (max/min): {:.1f}".format(x[min_idx_proc], Z.max()/zmin_proc))
            print("thread min: {:.0f},                 speedup (max/min): {:.1f}".format(y[min_idx_thread], Z.max()/zmin_thread))
            ax.plot([xmin], [ymin], [zmin], 'go', ms=5)
            ax.plot([xmin_proc], [ymin_proc], [zmin_proc], 'ro', ms=5)
            ax.plot([xmin_thread], [ymin_thread], [zmin_thread], 'ro', ms=5)
            ax.set_xlabel('procs')
            ax.set_ylabel('threads')
            ax.set_zlabel('timing (s)')
            ax.view_init(20,60)
            ax.plot_wireframe(X,Y,Z)
            ax.scatter(xx, yy, zz)
            ax.set_title(title)
            savefig(fig, '{}_{}'.format(study, maxsize_str))

    plt.show()

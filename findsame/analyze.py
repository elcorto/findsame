import os

import numpy as np
from matplotlib import pyplot as plt

from findsame import main, common as co


def collect_file_sizes(files_dirs):
    """1d array with file sizes for all files and dirs (recursive) in
    `files_dirs` in bytes.

    Parameters
    ----------
    files_dirs : list of strings
        files and dirs, the returned array contains the sizes of all files
        found
    """
    # MekleTree is actually not needed here, as well as FileDirTree which is
    # used in there, sice we are only interested in the files, not the tree. We
    # could do what we need here by using os.walk and replicate a part of
    # FileDirTree.build_tree(), but we are lazy.
    mt = main.get_merkle_tree(files_dirs)
    return np.array([leaf.filesize for leaf in mt.tree.leafs.values()],
                    dtype=np.float64)


class DataDir:
    """A dir on which we ran a benchmark and/or want to calculate a file size
    histogram using self.sizes. (Calculate and) store bookkeeping data (path,
    file sizes array, ...).
    """
    def __init__(self, path, alias=None, tmpdir='/tmp/findsame_datadir_cache'):
        self.path = path
        self.alias = alias
        cache_fn = os.path.join(tmpdir, path.replace('/','_')) + '.npy'
        if os.path.exists(cache_fn):
            self.sizes = np.load(cache_fn)
        else:
            self.sizes = collect_file_sizes([self.path])
            os.makedirs(tmpdir, exist_ok=True)
            np.save(cache_fn, self.sizes)
        self.cache_fn = cache_fn
        self.size_str = co.size2str(self.sizes.sum())

    def __repr__(self):
        if self.alias is None:
            return f"{self.path}"
        else:
            return f"{self.alias}:{self.path}"


def get_log_pow(logbase):
    return lambda x: np.log(x)/np.log(logbase), lambda x: np.power(logbase, x)


def histogram(xin, bins=100, norm=False, logx=True, logbase=10, density=False):
    if logx:
        flog, fpow = get_log_pow(logbase)
        xi = xin[xin > 0]
        bin_arr = fpow(np.linspace(flog(xi.min()), flog(xi.max()), bins))
    else:
        xi = xin
        bin_arr = np.histogram_bin_edges(xi, bins=bins)
    hh,be = np.histogram(xi, bins=bin_arr, density=density)
    if norm:
        hh = hh / np.dot(hh, np.diff(be))
    return hh, be


def hist(_xlst, bins=100, norm=False, shift_fac=0.8, labels=None,
         logx=True, ax=None, logbase=10, density=False):
    """As in plt.hist, plot multiple histograms for each x in xlst, but use
    x-axis log scale if logx=True (plt.hist(..., log=True) applies to y).
    Optional normalization to sum of bin areas = 1. Use step plots for each
    histogram, and shift them along y if shift_fac > 0.

    Parameters
    ----------
    xlst : list of 1d arrays

    Returns
    -------
    fig, ax

    Notes
    -----
    When logx=True, we exclude empty files b/c of the log scale.

    When len(xlst) > 1 and shift_fac > 0, histograms are shifted along y for
    better visability. In that case we turn of y ticks (the bin counts) since
    it makes no sense in that case.
    """
    xlst = [_xlst] if isinstance(_xlst, np.ndarray) else _xlst
    if labels is not None:
        assert len(xlst) == len(labels)

    if ax is None:
        fig,ax = plt.subplots()
    else:
        fig = ax.get_figure()
    lastmax = 0.0
    for ii,xi in enumerate(xlst):
        hh,be = histogram(xi, bins=bins, logx=logx, norm=norm,
                          logbase=logbase, density=density)
        label = None if labels is None else labels[ii]
        ax.step(be[:-1] + 0.5*np.diff(be), hh + lastmax, label=label, lw=2,
                where='mid')
        lastmax += hh.max() * shift_fac
    if logx:
        ax.set_xscale('log', basex=logbase)
    ax.set_xticklabels([co.size2str(int(x)) for x in ax.get_xticks()])
    if len(xlst) > 1 and shift_fac > 0:
        ax.set_yticklabels([])
        ax.set_yticks([])
    if labels is not None:
        ax.legend()
    return fig,ax

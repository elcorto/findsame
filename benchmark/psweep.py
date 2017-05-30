"""
The basic data structure for param study is a list `params` of parameter sets
(``pset``s).

params = [{'foo': 1, 'bar': 'lala'},  # pset 1
          {'foo': 2, 'bar': 'zzz'},   # pset 2
          ...                         # ...
         ]

Each pset contains values to parameters ('foo' and 'bar') which are varied
during the parameter study.

These psets are the basis of a pandas DataFrame (much like an SQL table, 2D array
w/ named columns and in case of DataFrame also variable data types) with
columns 'foo' and 'bar'. 

Then we define a callback function `func`, which takes only one pset
such as::

    {'foo': 1, 'bar': 'lala'},

and runs the workload for that pset. `func` must return a dict, for example::

    {'timing': 1.234}, 

which is the result of the run.

`func` is called in a loop on all psets in `params` in the `run` helper
function. The result dict (e.g. ``{'timing': ...}`` from each call gets merged
with the current pset and appended to a DataFrame, thus creating a new column
called 'timing'.

Below we have some helper functions which assist in creating `params`.
Basically, we define the to-be-varied parameters as "named sequences" (i.e.
list of dicts) which are,in fact, the columns of `params`. Then we use
something like itertools.product to loop over them.

    >>> from itertools import product
    >>> x=seq2dicts('a', [1,2,3])
    >>> x
    [{'x': 1}, {'x': 2}, {'x': 3}]
    >>> y=seq2dicts('y', ['xx','yy','zz'])
    >>> y
    [{'y': 'xx'}, {'y': 'yy'}, {'y': 'zz'}]
    >>> list(product(x,y))
    [({'x': 1}, {'y': 'xx'}),
     ({'x': 1}, {'y': 'yy'}),
     ({'x': 1}, {'y': 'zz'}),
     ({'x': 2}, {'y': 'xx'}),
     ({'x': 2}, {'y': 'yy'}),
     ({'x': 2}, {'y': 'zz'}),
     ({'x': 3}, {'y': 'xx'}),
     ({'x': 3}, {'y': 'yy'}),
     ({'x': 3}, {'y': 'zz'})]

    >>> loops2params(product(x,y))
    [{'x': 1, 'y': 'xx'},
     {'x': 1, 'y': 'yy'},
     {'x': 1, 'y': 'zz'},
     {'x': 2, 'y': 'xx'},
     {'x': 2, 'y': 'yy'},
     {'x': 2, 'y': 'zz'},
     {'x': 3, 'y': 'xx'},
     {'x': 3, 'y': 'yy'},
     {'x': 3, 'y': 'zz'}]

The logic of the param study is entirely contained in the creation of `params`.
E.g., if parameters shall be varied together (say x and y), then instead of

    >>> product(x,y,z)

use

    >>> product(zip(x,y), z)

The nestings from zip() are flattened in loops2params().

    >>> z=seq2dicts('z', [None, 1.2, 'X'])
    >>> z
    [{'z': None}, {'z': 1.2}, {'z': 'X'}]
    >>> list(product(zip(x,y),z))
    [(({'x': 1}, {'y': 'xx'}), {'z': None}),
     (({'x': 1}, {'y': 'xx'}), {'z': 1.2}),
     (({'x': 1}, {'y': 'xx'}), {'z': 'X'}),
     (({'x': 2}, {'y': 'yy'}), {'z': None}),
     (({'x': 2}, {'y': 'yy'}), {'z': 1.2}),
     (({'x': 2}, {'y': 'yy'}), {'z': 'X'}),
     (({'x': 3}, {'y': 'zz'}), {'z': None}),
     (({'x': 3}, {'y': 'zz'}), {'z': 1.2}),
     (({'x': 3}, {'y': 'zz'}), {'z': 'X'})]

    >>> loops2params(product(zip(x,y),z))
    [{'x': 1, 'y': 'xx', 'z': None},
     {'x': 1, 'y': 'xx', 'z': 1.2},
     {'x': 1, 'y': 'xx', 'z': 'X'},
     {'x': 2, 'y': 'yy', 'z': None},
     {'x': 2, 'y': 'yy', 'z': 1.2},
     {'x': 2, 'y': 'yy', 'z': 'X'},
     {'x': 3, 'y': 'zz', 'z': None},
     {'x': 3, 'y': 'zz', 'z': 1.2},
     {'x': 3, 'y': 'zz', 'z': 'X'}]

If you want a parameter which is constant, use a length one list and put it in
the loops:

    >>> c=seq2dicts('c', ['const'])
    >>> loops2params(product(zip(x,y),z,c))
    [{'a': 1, 'c': 'const', 'y': 'xx', 'z': None},
     {'a': 1, 'c': 'const', 'y': 'xx', 'z': 1.2},
     {'a': 1, 'c': 'const', 'y': 'xx', 'z': 'X'},
     {'a': 2, 'c': 'const', 'y': 'yy', 'z': None},
     {'a': 2, 'c': 'const', 'y': 'yy', 'z': 1.2},
     {'a': 2, 'c': 'const', 'y': 'yy', 'z': 'X'},
     {'a': 3, 'c': 'const', 'y': 'zz', 'z': None},
     {'a': 3, 'c': 'const', 'y': 'zz', 'z': 1.2},
     {'a': 3, 'c': 'const', 'y': 'zz', 'z': 'X'}]

So, as you can see, the general idea is that we do all the loops *before*
running any workload, i.e. we assemble the parameter grid to be sampled before
the actual calculations. This has proven to be vey practical as it helps
detecting errors early.
"""

from io import IOBase
from itertools import product
import os, copy
import pandas as pd

def seq2dicts(name, seq):
    """
    >>> seq2dicts('a', [1,2,3])
    [{'a': 1}, {'a': 2}, {'a': 3}]
    """
    return [{name: entry} for entry in seq]


def merge_dicts(lst):
    dct = {}
    for entry in lst:
        dct.update(entry)
    return dct


# stolen from pwtools and adapted for python3
def is_seq(seq):
    if isinstance(seq, str) or \
       isinstance(seq, IOBase) or \
       isinstance(seq, dict):
        return False
    else:
        try:
            _ = iter(seq)
            return True
        except:
            return False


def flatten(seq):
    for item in seq:
        if not is_seq(item):
            yield item
        else:
            for subitem in flatten(item):
                yield subitem


def params2df(params):
    df = pd.DataFrame()
    for idx,dct in enumerate(params):
        df = df.append(pd.DataFrame(dct, index=[idx]))
    return df


def mkparams(*args):
    return loops2params(product(*args))


def loops2params(loops):
    return [merge_dicts(flatten(entry)) for entry in loops]


# XXX possible API change:
#  run(func, params, df=None):
#      df = pd.DataFrame() if df is None else df
# also write out df after each iteration, save already finished stuff to deal
# with crashing func() calls at some later pset
def run(df, func, params):
    for idx,pset in enumerate(params):
        row = copy.deepcopy(pset)
        row.update(func(pset))
        df_row = pd.DataFrame(row, index=[idx])
        df = df.append(df_row)
        print(df_row)
    return df



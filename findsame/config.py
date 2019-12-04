import copy

class Config(dict):
    """Dict subclass with attribute access.

    https://stackoverflow.com/a/25978130
    """
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.__dict__ = self


# These are default values. They are designed to be changed from outside (see
# main) and thus change the bahavior of the package. To retain a copy of the
# original defaults, we have default_cfg.
cfg = Config(nprocs=1,
             nthreads=1,
             blocksize=256*1024,
             share_leafs=True,
             limit=None,
             auto_limit_min=8*1024,
             auto_limit_increase_fac=2,
             auto_limit_converged=3,
             outmode=3,
             verbose=False,
             )

default_cfg = copy.deepcopy(cfg)

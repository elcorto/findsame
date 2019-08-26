class Config:
    def __init__(self, *args, **kwds):
        for kk,vv in kwds.items():
            setattr(self, kk, vv)

    def __repr__(self):
        return self.__dict__.__repr__()

    def update(self, dct):
        for kk,vv in dct.items():
            setattr(self, kk, vv)


# defaults
cfg = Config(nprocs=1,
             nthreads=1,
             blocksize=256*1024,
             share_leafs=True,
             limit=None,
             auto_limit_min=8*1024,
             auto_limit_increase_fac=2,
             outmode=1,
             verbose=False,
             )

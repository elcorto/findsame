import copy

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
_cfg = Config(nprocs=1, 
              nthreads=1, 
              blocksize=256*1024, 
              share_leafs=True,
              limit=None,
              outmode=1,
              verbose=False,
              )

def getcfg():
    return copy.deepcopy(_cfg)

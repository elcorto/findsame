class Config:
    def __init__(self, *args, **kwds):
        for kk,vv in kwds.items():
            setattr(self, kk, vv)
    def update(self, dct):
        for kk,vv in dct.items():
            setattr(self, kk, vv)
            

# defaults
config = Config(nprocs=1, 
                nthreads=1, 
                blocksize=256*1024, 
                share_leafs=True,
                limit=None,
                )

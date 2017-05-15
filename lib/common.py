KiB = 1024
MiB = KiB**2
GiB = KiB**3
UNITS = [(GiB, 'G'), (MiB, 'M'), (KiB, 'K'), (1, '')]
INV_UNITS = dict((vv,kk) for kk,vv in UNITS)


def size2str(filesize, sep='', prec=1):
    """Convert size in bytes to string with unit."""
    for unit, symbol in UNITS:
        if filesize // unit == 0:
            continue
        else:
            fmt = "{{:.{prec}f}}{{}}{{}}".format(prec=prec)
            return fmt.format(filesize/unit, sep, symbol)


def str2size(st, sep=''):
    if st[-1] in INV_UNITS.keys():
        if sep == '':
            unit = st[-1]
            number = st[:-1]
        else:
            split = st.split(sep)
            assert len(split) == 2
            unit = split[1]
            number = split[0]
    else:
        unit = ''
        number = st
    return int(float(number) * INV_UNITS[unit])


def invert_dict(dct):
    """Given a dict with paths and hashes, "invert" the dict to find all paths
    which have the same hash.

    Parameters
    ----------
    dct: dict
        {path1: hashA,
         path2: hashA,
         path3: hashB,
         ...}

    Returns
    -------
    dict
        {hashA: [path1, path2],
         hashB: [path3],
         ...}
    """
    store = dict()
    for path,hsh in dct.items():
        if hsh in store.keys():
            store[hsh].append(path)
        else:
            store[hsh] = [path]
    # sort to force reproducible results
    return dict((k,sorted(v)) for k,v in store.items())


def dict_equal(aa, bb):
    if set(aa.keys()) != set(bb.keys()):
        print("keys not equal:\naa: {}\nbb: {}".format(aa.keys(), bb.keys()))
        return False
    for akey, aval in aa.items():
        xx = aval
        yy = bb[akey]
        if isinstance(aval, dict):
            if not dict_equal(xx, yy):
                return False
        else:
            if not xx == yy:
                print("vals not equal:\naa: {}\nbb: {}".format(xx, yy))
                return False
    return True



class lazyprop(object):
    """Decorator for creating lazy evaluated properties.
    The property should represent non-mutable data, as it replaces itself.
    
    kudos: Cyclone over at stackoverflow!
    http://stackoverflow.com/questions/3012421/python-lazy-property-decorator
    """
    def __init__(self,fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self,obj,cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj,self.func_name,value)
        return value


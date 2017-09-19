# publish on pypi
# ---------------
#   $ python3 setup.py sdist
#   $ twine upload dist/<this-package>-x.y.z.tar.gz 

import os, importlib
from setuptools import setup, find_packages
from distutils.version import StrictVersion as Version

here = os.path.abspath(os.path.dirname(__file__))
bindir = 'bin'
with open(os.path.join(here, 'README.rst')) as fd:
    long_description = fd.read()

# Hack to make pip respect system packages. So sad! Why in the world can pip
# list and uninstall system packages (Debian: /usr/lib/python3/dist-packages),
# but NOT respect them when installing!!!?? It completely ignores existing
# packages, even with correct versions, and happily re-installs them from
# it's own sources (of course to other locations). Then we end up with two
# installations of the SAME package in the SAME version -- thank you very much.
# I don't get it, seriously.
install_requires = []

req = [('matplotlib', 'matplotlib', None, None),
       ('nose', 'nose', None, None),
       ('numpy', 'numpy', None, None),
       ('psweep', 'psweep', None, None),
       ]

for pipname,pkgname,op,ver in req:
    print("checking dependency: {}".format(pkgname))
    req = pipname + op + ver if op and ver else pipname
    try:
        pkg = importlib.import_module(pkgname)
        if op and ver:
            cmd = "Version(pkg.__version__) {op} Version('{ver}')".format(op=op,
                                                                          ver=ver)
            if not eval(cmd):
                install_requires.append(req)
    except ImportError:
        install_requires.append(req)


setup(
    name='findsame',
    version='0.0.0',
    description='Find duplicate files and directories',
    long_description=long_description,
    url='https://github.com/elcorto/findsame',
    author='Steve Schmerler',
    author_email='git@elcorto.com',
    license='GPLv3',
    keywords='same files directories merkle tree hash',
    packages=find_packages(),
    install_requires=install_requires,
    scripts=['{}/{}'.format(bindir, script) for script in os.listdir(bindir)]
)

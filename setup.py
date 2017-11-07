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

# Hack to make pip respect system packages. 
install_requires = []

# (pip name, import name, operator, version)
# ('numpy', 'numpy', '>', '1.0')
reqs = [('matplotlib', 'matplotlib', None, None),
        ('nose', 'nose', None, None),
        ('pandas', 'pandas', None, None),
        ('numpy', 'numpy', None, None),
        ('psweep', 'psweep', None, None),
        ]

for pip_name,import_name,op,ver in reqs:
    print("checking dependency: {}".format(import_name))
    req = pip_name + op + ver if op and ver else pip_name
    try:
        pkg = importlib.import_module(import_name)
        if op and ver:
            cmd = "Version(pkg.__version__) {op} Version('{ver}')".format(op=op,
                                                                          ver=ver)
            if not eval(cmd):
                install_requires.append(req)
    except ImportError:
        install_requires.append(req)

print("install_requires: {}".format(install_requires))

setup(
    name='findsame',
    version='0.0.0',
    description='Find duplicate files and directories',
    long_description=long_description,
    url='https://github.com/elcorto/findsame',
    author='Steve Schmerler',
    author_email='git@elcorto.com',
    license='BSD 3-Clause',
    keywords='same files directories merkle tree hash',
    packages=find_packages(),
    install_requires=install_requires,
    scripts=['{}/{}'.format(bindir, script) for script in os.listdir(bindir)]
)

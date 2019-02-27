# publish on pypi
# ---------------
#   $ python3 setup.py sdist
#   $ twine upload dist/<this-package>-x.y.z.tar.gz

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
bindir = 'bin'
with open(os.path.join(here, 'README.rst')) as fd:
    long_description = fd.read()


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
    install_requires=open('requirements.txt').read().splitlines(),
    scripts=['{}/{}'.format(bindir, script) for script in os.listdir(bindir)]
)

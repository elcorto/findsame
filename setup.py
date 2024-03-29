import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
bindir = 'bin'
with open(os.path.join(here, 'README.rst')) as fd:
    long_description = fd.read()


setup(
    name='findsame',
    version='0.1.2',
    description='Find duplicate files and directories using hashes and a Merkle tree',
    long_description=long_description,
    url='https://github.com/elcorto/findsame',
    author='Steve Schmerler',
    author_email='git@elcorto.com',
    license='BSD 3-Clause',
    keywords='merkle-tree hash duplicates multithreading multiprocessing',
    packages=find_packages(include=('findsame',),
                           exclude=('findsame/test', 'benchmark')),
    scripts=[f'{bindir}/{script}' for script in os.listdir(bindir)]
)

from setuptools import setup

import iast

setup(
    name='iAST',
    version=iast.__version__,
    
    author='Jon Brandvein',
    license='MIT License',
    description='A library for manipulating Python ASTs',
    
    packages=['iast'],
)

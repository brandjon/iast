"""Subpackage for Python-specific AST definitions and utilities.

All the code concerning Python 3.3's AST and Python 3.4's AST is
exported from the modules python33.py and python34.py respectively.
The namespace of the subpackage itself serves as an alias for
whichever version corresponds to the currently executing Python
interpreter.
"""


__all__ = [
    # ...
]


import sys


ver = sys.version_info
if ver[:2] == (3, 3):
    from . import python33 as python
elif ver[:2] == (3, 4):
    from . import python34 as python
else:
    raise AssertionError('Unsupported Python version')

__all__.extend(python.__all__)
globals().update({k: python.__dict__[k] for k in python.__all__})

"""Alias for python33.py or python34.py."""


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

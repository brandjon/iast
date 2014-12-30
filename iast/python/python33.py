"""Export Python 3.3 nodes and utilities."""


__all__ = [
    'py_nodes',
    # ...
]


import sys


# Include node classes.
from .pynode import py33_nodes as py_nodes
__all__.extend(py_nodes.keys())
globals().update(py_nodes)

# Include native features if version matches.
if sys.version_info[:2] == (3, 3):
    from . import native
    __all__.extend(native.__all__)
    globals().update({k: native.__dict__[k] for k in native.__all__})

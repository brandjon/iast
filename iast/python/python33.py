"""Export Python 3.3 nodes and utilities."""


__all__ = [
    # ...
]


import sys


def include(keys, mapping):
    __all__.extend(keys)
    globals().update({k: mapping[k] for k in keys})

def include_mod(mod):
    include(mod.__all__, mod.__dict__)


# Include node classes.
from .pynode import py33_nodes as py_nodes
__all__.append('py_nodes')
include(py_nodes, py_nodes)

# Include native features if version matches.
if sys.version_info[:2] == (3, 3):
    from . import native
    include_mod(native)

# Include patterns.
from . import pypattern
include_mod(pypattern)

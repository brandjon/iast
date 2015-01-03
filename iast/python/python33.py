"""Export Python 3.3 nodes and utilities."""


__all__ = [
    # ...
]


import sys


def include_dict(mapping):
    __all__.extend(mapping.keys())
    globals().update(mapping)

def include_mod(mod):
    # Use get_all() if defined, otherwise use module's __dict__.
    get_all = getattr(mod, 'get_all', None)
    if get_all is not None:
        thismod = sys.modules[__name__]
        entries = get_all(thismod)
        include_dict(entries)
    else:
        include_dict({k: mod.__dict__[k] for k in mod.__all__})


# Include node classes.
from .pynode import py33_nodes as py_nodes
__all__.append('py_nodes')
include_dict(py_nodes)

# Include native features if version matches.
if sys.version_info[:2] == (3, 3):
    from . import native
    include_mod(native)

# Include utils.
from . import pyutil
include_mod(pyutil)

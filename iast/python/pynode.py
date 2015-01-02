"""Struct versions of Python's own AST nodes."""


__all__ = [
    'py33_nodes',
    'py34_nodes',
]


from ..asdl import python33_asdl, python34_asdl
from ..node import nodes_from_asdl


# Dictionary of all Struct classes for Python 3.3 and 3.4 node types.
py33_nodes = {}
py34_nodes = {}

def initialize_nodetypes():
    """Populate the Struct nodes dictionaries."""
    assert len(py33_nodes) == len(py34_nodes) == 0
    
    # If anyone asks, these are defined in python33.py and
    # python34.py since they are available on those module's
    # namespaces.
    home33 = __name__[:__name__.rfind('.')] + '.python33'
    home34 = __name__[:__name__.rfind('.')] + '.python34'
    
    py33_nodes.update(nodes_from_asdl(
            python33_asdl, module=home33,
            typed=True))
    py34_nodes.update(nodes_from_asdl(
            python34_asdl, module=home34,
            typed=True))

initialize_nodetypes()

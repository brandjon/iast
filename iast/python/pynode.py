"""Struct versions of Python's own AST nodes."""


__all__ = [
    'py33_nodes',
    'py34_nodes',
]


from ..asdl import primitive_types, python33_asdl, python34_asdl
from ..node import nodes_from_asdl


# Dictionary of all Struct classes for Python 3.3 and 3.4 node types.
py33_nodes = {}
py34_nodes = {}

def initialize_nodetypes():
    """Populate the Struct nodes dictionaries."""
    assert len(py33_nodes) == len(py34_nodes) == 0
    py33_nodes.update(nodes_from_asdl(
            python33_asdl, module=__name__,
            typed=True, primitive_types=primitive_types))
    py34_nodes.update(nodes_from_asdl(
            python34_asdl, module=__name__,
            typed=True, primitive_types=primitive_types))

initialize_nodetypes()

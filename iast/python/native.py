"""Interoperability with native nodes.

"Native" nodes is our term for the node classes defined in the
"ast" standard library module. We support conversion between
Struct nodes and native nodes, and parsing of source code into
Struct nodes -- but only for the version of the grammar matching
the currently executing Python interpreter.
"""


__all__ = [
    'native_nodes',
    'pyToStruct',
    'structToPy',
    'parse',
]


import ast
import sys

from ..util import trim
from ..node import AST
from .pynode import py33_nodes, py34_nodes


# Dictionary of all node classes in the ast library.
native_nodes = {nodecls.__name__: nodecls
                for nodecls in ast.__dict__.values()
                if isinstance(nodecls, type)
                if issubclass(nodecls, ast.AST)}


# Alias for nodes dictionary matching current interpreter version.
ver = sys.version_info
if ver[:2] == (3, 3):
    py_nodes = py33_nodes
elif ver[:2] == (3, 4):
    py_nodes = py34_nodes
else:
    raise AssertionError('Unsupported Python version')


def convert_ast(tree, to_struct):
    """Convert from native nodes to Struct nodes if to_struct is
    True; otherwise convert in the opposite direction.
    """
    base = ast.AST if to_struct else AST
    mapping = py_nodes if to_struct else native_nodes
    seqtype = tuple if to_struct else list
    
    if isinstance(tree, base):
        name = tree.__class__.__name__
        out_type = mapping[name]
        field_values = []
        for field in tree._fields:
            fval = getattr(tree, field, None)
            fval = convert_ast(fval, to_struct)
            field_values.append(fval)
        new_tree = out_type(*field_values)
        return new_tree
    elif isinstance(tree, (list, tuple)):
        return seqtype(convert_ast(item, to_struct) for item in tree)
    else:
        return tree

def pyToStruct(tree):
    """Convert from a native AST to a Struct AST."""
    assert isinstance(tree, ast.AST)
    return convert_ast(tree, to_struct=True)

def structToPy(tree):
    """Convert from a Struct AST to a native AST."""
    assert isinstance(tree, AST)
    return convert_ast(tree, to_struct=False)


def parse(source):
    """Like ast.parse(), but produce a Struct AST. Works with indented
    triple-quoted literals (via util.trim())."""
    source = trim(source)
    tree = ast.parse(source)
    tree = pyToStruct(tree)
    return tree

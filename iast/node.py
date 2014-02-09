"""Defines Struct-based versions of the standard Python nodes."""

# TODO: for some reason it looks like calling type() directly
# causes the struct nodes to have a __module__ of simplestruct.struct.

import ast
from collections import OrderedDict

from simplestruct import Struct, Field


__all__ = [
    'AST',
    
    # Entries for AST nodes inserted programmatically.
    
    'convert_ast',
    'pyToStruct',
    'structToPy',
]


# Python node classes.
py_nodes = {name: nodecls for name, nodecls in ast.__dict__.items()
                          if isinstance(nodecls, type)
                          if issubclass(nodecls, ast.AST)}

# Root of struct node class hierarchy.
class AST(Struct):
    pass

# Struct node classes
struct_nodes = {'AST': AST}

# Define struct nodes programmatically.
for name, pnode in py_nodes.items():
    if name == 'AST':
        continue
    namespace = OrderedDict((f, Field()) for f in pnode._fields)
    namespace['_fields'] = tuple(pnode._fields)
    snode = type(pnode.__name__, (AST,), namespace)
    globals()[pnode.__name__] = snode
    struct_nodes[name] = snode
    __all__.append(name)


def convert_ast(value, to_struct=True):
    """Convert between Python AST nodes and struct nodes.
    The direction is given by to_struct. value may be a node,
    list of nodes, or non-node value.
    """
    base = ast.AST if to_struct else AST
    mapping = struct_nodes if to_struct else py_nodes
    
    if isinstance(value, base):
        name = value.__class__.__name__
        out_type = mapping[name]
        field_values = []
        for field in value._fields:
            fval = getattr(value, field, None)
            fval = convert_ast(fval)
            field_values.append(fval)
        new_value = out_type(*field_values)
        return new_value
    elif isinstance(value, list):
        return [convert_ast(item) for item in value]
    else:
        return value

def pyToStruct(value):
    """Turn a Python AST to a struct AST."""
    assert isinstance(value, ast.AST)
    return convert_ast(value)

def structToPy(value):
    """Turn a struct AST to a Python AST."""
    assert isinstance(value, AST)
    return convert_ast(value, to_struct=False)

"""Defines Struct-based versions of the standard Python nodes."""

import ast
from collections import OrderedDict

from simplestruct import Struct, Field


__all__ = [
    'AST',
    
    # Entries for AST nodes inserted programmatically.
    
    'pyToStruct',
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
    namespace = OrderedDict((f, Field()) for f in pnode._fields)
    namespace['_fields'] = tuple(pnode._fields)
    snode = type(pnode.__name__, (AST,), namespace)
    globals()[pnode.__name__] = snode
    struct_nodes[name] = snode
    __all__.append(name)


def pyToStruct(value):
    """Recursively turn a Python AST into a struct AST.
    value may be a Python AST node, a list of nodes, or a
    non-node value.
    """
    if isinstance(value, ast.AST):
        name = value.__class__.__name__
        struct_type = struct_nodes[name]
        field_values = []
        for field in value._fields:
            fval = getattr(value, field, None)
            fval = pyToStruct(fval)
            field_values.append(fval)
        new_value = struct_type(*field_values)
        return new_value
    elif isinstance(value, list):
        return [pyToStruct(item) for item in value]
    else:
        return value

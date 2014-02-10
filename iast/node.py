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
    'parse',
    'dump',
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


def convert_ast(value, to_struct):
    """Convert between Python AST nodes and struct nodes.
    The direction is given by to_struct. value may be a node,
    list of nodes, or non-node value.
    """
    base = ast.AST if to_struct else AST
    mapping = struct_nodes if to_struct else py_nodes
    seqtype = tuple if to_struct else list
    
    if isinstance(value, base):
        name = value.__class__.__name__
        out_type = mapping[name]
        field_values = []
        for field in value._fields:
            fval = getattr(value, field, None)
            fval = convert_ast(fval, to_struct)
            field_values.append(fval)
        new_value = out_type(*field_values)
        return new_value
    elif isinstance(value, (list, tuple)):
        return seqtype(convert_ast(item, to_struct) for item in value)
    else:
        return value

def pyToStruct(value):
    """Turn a Python AST to a struct AST."""
    assert isinstance(value, ast.AST)
    return convert_ast(value, to_struct=True)

def structToPy(value):
    """Turn a struct AST to a Python AST."""
    assert isinstance(value, AST)
    return convert_ast(value, to_struct=False)

def parse(source):
    """Like ast.parse(), but produce a struct AST."""
    tree = ast.parse(source)
    tree = pyToStruct(tree)
    return tree


def dump(value, col=0):
    """A multi-line struct-AST pretty-printer."""
    if isinstance(value, AST):
        functor = value.__class__.__name__ + '('
        newcol = col + len(functor)
        delim = ',\n' + (' ' * newcol)
        return (functor +
                delim.join(key + ' = ' + dump(item, len(key) + 3 + newcol)
                           for key, item in value._asdict().items()) +
                ')')
    elif isinstance(value, tuple):
        newcol = col + 1
        delim = ',\n' + (' ' * newcol)
        return ('[' +
                delim.join(dump(item, newcol) for item in value) +
                ']')
    else:
        return repr(value)

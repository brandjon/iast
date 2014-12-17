"""Struct versions of Python's own AST nodes."""


__all__ = [
    # Entries for AST nodes inserted programmatically.
    'convert_ast',
    'pyToStruct',
    'structToPy',
    'parse',
]


import ast

from .util import trim
from .node import AST


# Python node classes.
py_nodes = {name: nodecls for name, nodecls in ast.__dict__.items()
                          if isinstance(nodecls, type)
                          if issubclass(nodecls, ast.AST)}

# Struct node classes
struct_nodes = {'AST': AST}

# Define struct nodes programmatically.
for name, pnode in py_nodes.items():
    if name == 'AST':
        continue
    namespace = {'__module__': __name__,
                 '_fields': tuple(pnode._fields)}
    snode = type(pnode.__name__, (AST,), namespace)
    globals()[pnode.__name__] = snode
    struct_nodes[name] = snode
    __all__.append(name)
# Fix bases (must happen after since bases aren't necessarily
# transferred before subclasses).
for name, snode in struct_nodes.items():
    if name == 'AST':
        continue
    (base,) = py_nodes[name].__bases__
    base = struct_nodes[base.__name__]
    snode.__bases__ = (base,)


def convert_ast(tree, to_struct):
    """Convert between Python AST nodes and struct nodes.
    The direction is given by to_struct. tree may be a node,
    list of nodes, or non-node tree.
    """
    base = ast.AST if to_struct else AST
    mapping = struct_nodes if to_struct else py_nodes
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
    """Turn a Python AST to a struct AST."""
    assert isinstance(tree, ast.AST)
    return convert_ast(tree, to_struct=True)

def structToPy(tree):
    """Turn a struct AST to a Python AST."""
    assert isinstance(tree, AST)
    return convert_ast(tree, to_struct=False)


def parse(source):
    """Like ast.parse(), but produce a struct AST. Works with indented
    triple-quoted literals (via simplestruct.trim())."""
    source = trim(source)
    tree = ast.parse(source)
    tree = pyToStruct(tree)
    return tree

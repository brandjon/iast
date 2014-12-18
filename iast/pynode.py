"""Struct versions of Python's own AST nodes.

To avoid ambiguity, we refer to the normal (non-Struct) AST node
classes that are defined in the "ast" standard library as "native
Python nodes".
"""


__all__ = [
    # Entries for each AST node type get inserted
    # into __all__ programmatically.
    'nodes',
    'convert_ast',
    'pyToStruct',
    'structToPy',
    'parse',
]


import ast

from .util import trim
from .node import AST


# Dictionary of all node classes in the ast library.
native_nodes = {nodecls.__name__: nodecls
                for nodecls in ast.__dict__.values()
                if isinstance(nodecls, type)
                if issubclass(nodecls, ast.AST)}

# Dictionary of all Struct classes for Python node types.
nodes = {'AST': AST}

def initialize_nodetypes():
    """Populate the nodes dictionary."""
    for name, py_node in native_nodes.items():
        # Class hierarchy root is already defined in node.py.
        if name == 'AST':
            continue
        # __module__ needs to be included in the namespace because
        # classes created using type() do not get it set automatically.
        namespace = {'__module__': __name__,
                     '_fields': tuple(py_node._fields)}
        new_node = type(name, (AST,), namespace)
        globals()[py_node.__name__] = new_node
        nodes[name] = new_node
        __all__.append(name)
    # Set up bases. Must happen after since Struct classes are created
    # in arbitrary order.
    for name, node in nodes.items():
        if name == 'AST':
            continue
        # Each node has exactly one base class.
        (base,) = native_nodes[name].__bases__
        base = nodes[base.__name__]
        node.__bases__ = (base,)

initialize_nodetypes()


def convert_ast(tree, to_struct):
    """Convert from native nodes to Struct nodes if to_struct is
    True; otherwise convert in the opposite direction.
    """
    base = ast.AST if to_struct else AST
    mapping = nodes if to_struct else native_nodes
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
    """Like ast.parse(), but produce a struct AST. Works with indented
    triple-quoted literals (via util.trim())."""
    source = trim(source)
    tree = ast.parse(source)
    tree = pyToStruct(tree)
    return tree

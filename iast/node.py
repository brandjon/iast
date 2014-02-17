"""Defines Struct-based versions of the standard Python nodes."""

# TODO: for some reason it looks like calling type() directly
# causes the struct nodes to have a __module__ of simplestruct.struct.


import ast
from collections import OrderedDict

from simplestruct import Struct, Field, MetaStruct
from simplestruct.util import trim


__all__ = [
    'AST',
    
    # Entries for AST nodes inserted programmatically.
    
    'convert_ast',
    'pyToStruct',
    'structToPy',
    'parse',
    'dump',
]


class MetaAST(MetaStruct):
    
    """MetaStruct subclass for defining Struct AST nodes.
    
    Struct fields are auto-generated from the _fields tuple.
    """
    
    def __new__(mcls, clsname, bases, namespace, **kargs):
        # Make sure the namespace is an ordered mapping.
        namespace = OrderedDict(namespace)
        
        # Create if not present, ensure sequence is a tuple.
        fields = tuple(namespace.get('_fields', ()))
        namespace['_fields'] = fields
        
        # For each field, if an explicit definition is not provided,
        # add one, and if it is provided, put it in the right order.
        for fname in fields:
            if fname not in namespace:
                namespace[fname] = Field()
            else:
                namespace.move_to_end(fname)
        
        return super().__new__(mcls, clsname, bases, namespace, **kargs)

# Root of struct node class hierarchy.
class AST(Struct, metaclass=MetaAST):
    pass


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
    namespace = {'_fields': tuple(pnode._fields)}
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


def dump(tree, col=0):
    """A multi-line struct-AST pretty-printer."""
    if isinstance(tree, AST):
        functor = tree.__class__.__name__ + '('
        newcol = col + len(functor)
        delim = ',\n' + (' ' * newcol)
        return (functor +
                delim.join(key + ' = ' + dump(item, len(key) + 3 + newcol)
                           for key, item in tree._asdict().items()) +
                ')')
    elif isinstance(tree, tuple):
        newcol = col + 1
        delim = ',\n' + (' ' * newcol)
        return ('[' +
                delim.join(dump(item, newcol) for item in tree) +
                ']')
    else:
        return repr(tree)

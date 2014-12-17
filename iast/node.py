"""Framework for Struct-based AST nodes."""


from collections import OrderedDict

from simplestruct import Struct, Field, MetaStruct


__all__ = [
    'AST',
    'dump',
]


class MetaAST(MetaStruct):
    
    """MetaStruct subclass for defining Struct AST nodes.
    
    Struct fields are auto-generated from the _fields tuple.
    """
    
    def __new__(mcls, clsname, bases, namespace, **kargs):
        # Make sure the namespace is an ordered mapping
        # for passing the fields to MetaStruct.
        namespace = OrderedDict(namespace)
        
        # Create _fields if not present, ensure sequence is a tuple.
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

class AST(Struct, metaclass=MetaAST):
    """Root of any Struct AST node class hierarchy."""


def dump(tree, indent=0):
    """A multi-line Struct-AST pretty-printer. Note that this is for
    getting the exact tree structure, not a source-like representation.
    
    If all non-node field values in the tree can be constructed from
    their reprs, then the returned string can be executed to reproduce
    the tree.
    """
    if isinstance(tree, AST):
        functor = tree.__class__.__name__ + '('
        new_indent = indent + len(functor)
        delim = ',\n' + (' ' * new_indent)
        return (functor +
                delim.join(key + ' = ' + dump(item, len(key) + 3 + new_indent)
                           for key, item in tree._asdict().items()) +
                ')')
    elif isinstance(tree, tuple):
        new_indent = indent + 1
        delim = ',\n' + (' ' * new_indent)
        end = ',)' if len(tree) == 1 else ')'
        return ('(' +
                delim.join(dump(item, new_indent) for item in tree) +
                end)
    else:
        return repr(tree)

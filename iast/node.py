"""Framework for Struct-based AST nodes."""


__all__ = [
    'AST',
    'dump',
    'nodes_from_asdl',
]


from collections import OrderedDict
from simplestruct import Struct, Field, MetaStruct


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


class ASTBuilder:
    
    """Given an ASDL structure, return a mapping from each name of
    an AST node to a tuple of information describing it. The tuple
    consists of:
    
        1) a list of field specifications, which are triples of a
           field name, a type name (either an ASDL primitive or
           another node type), and a quantifier ('', '?', or '*')
        
        2) the name of a base node type it inherits from
    """
    
    # In the style of asdl.VisitorBase.
    
    def run(self, mod):
        self.info = {}
        self.visit(mod)
        return self.info
    
    def visit(self, obj, *args):
        methname = 'visit' + obj.__class__.__name__
        meth = getattr(self, methname)
        return meth(obj, *args)
    
    def visitModule(self, mod):
        for dfn in mod.dfns:
            self.visit(dfn)
    
    def visitType(self, type):
        self.visit(type.value, str(type.name))
    
    def visitSum(self, sum, name):
        for t in sum.types:
            self.visit(t, name)
        self.info[name] = ([], 'AST')
    
    def visitConstructor(self, cons, name):
        fields = []
        for f in cons.fields:
            fields.append(self.visit(f, cons.name))
        self.info[cons.name] = (fields, name)
    
    def visitField(self, field, name):
        assert not (field.seq and field.opt)
        quant = '*' if field.seq else '?' if field.opt else ''
        return (field.name, field.type, quant)
    
    def visitProduct(self, prod, name):
        fields = []
        for f in prod.fields:
            fields.append(self.visit(f, name))
        self.info[name] = (fields, 'AST')

def nodes_from_asdl(asdl_tree, module=None):
    """Given an ASDL structure, return a mapping from node type
    names to node types. If module is given, it should be the
    name of a module whose global namespace will contain the
    returned node types. (This allows instances of the node
    classes to be pickled.)
    """
    lang = {'AST': AST}
    info = ASTBuilder().run(asdl_tree)
    for name, (fields, _base) in info.items():
        namespace = {'__module__': module,
                     '_fields': tuple(fn for fn, ft, fq in fields)}
        new_node = type(name, (AST,), namespace)
        lang[name] = new_node
    for name, node in lang.items():
        if name == 'AST':
            continue
        _fields, base = info[name]
        basecls = lang[base]
        node.__bases__ = (basecls,)
    return lang

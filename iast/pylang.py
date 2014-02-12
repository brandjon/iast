"""Templating system for substituting ASTs and creating AST macros."""


from iast.node import (AST, struct_nodes, stmt, expr,
                       Expr, Call, Name, Load, Attribute)
from iast.visitor import NodeTransformer
from iast.pattern import PatVar, PatternTransformer


__all__ = [
    'extract_mod',
    'NameExpander',
    'MacroProcessor',
    'PyMacroProcessor',
]


def extract_mod(tree, mode=None):
    """Process a tree to extract a subtree of the top-level
    Module node. Mode is one of the following strings:
    
        - mod:     the tree is returned unchanged (default)
        - code:    the Module's list of statements is returned
        - stmt_or_blank:  either a single statement or None is returned
        - stmt:    a single statement is returned. The Module must have
                       exactly one top-level statement.
        - expr:    an expression is returned. The Module must have
                       exactly one top-level statement, that is an
                       Expr node.
    """
    if mode == 'mod':
        pass
    
    elif mode == 'code':
        tree = tree.body
    
    elif mode == 'stmt_or_blank':
        if len(tree.body) == 0:
            return None
        elif len(tree.body) == 1:
            tree = tree.body[0]
        else:
            raise ValueError('Mode "{}" requires zero or one statements '
                             '(got {})'.format(mode, len(tree.body)))
        
    elif mode in ['stmt', 'expr']:
        if len(tree.body) != 1:
            raise ValueError('Mode "{}" requires exactly one statement '
                             '(got {})'.format(mode, len(tree.body)))
        tree = tree.body[0]
        if mode == 'expr':
            if not isinstance(tree, Expr):
                raise ValueError('Mode "{}" requires Expr node (got {})'
                                 .format(mode, type(tree).__name__))
            tree = tree.value
    
    elif mode is not None:
        raise ValueError('Unknown parse mode "' + mode + '"')
    
    return tree


class NameExpander(NodeTransformer):
    
    """Replace names with ASTs according to the given mapping."""
    
    def __init__(self, subst):
        self.subst = subst
    
    def visit_Name(self, node):
        return self.subst.get(node.id, None)


class MacroProcessor(PatternTransformer):
    
    """Substitutes specific function and method calls with ASTs.
    Works on the input tree in a bottom-up fashion.
    
    Four patterns are supported: function expressions (fe), function
    statements (fs), method expressions (me), and method statements
    (ms). The fe and fs patterns match a function call where the
    function is syntactically specified by a Name node. The me and ms
    patterns apply to method calls. All of these patterns require that
    the call have no fancy arguments (i.e. no keywords, varargs, etc.).
    
    Handlers are defined as methods in subclasses, similar to visit_*
    methods in NodeVisitor subclasses. The names have form
    
        handle_KIND_NAME
    
    where KIND is one of the four pattern types ("fe", etc.) and NAME
    is the syntactic function or method name to match.
    
    Handlers take in two arguments: the function name and a tuple of
    the syntactic argument ASTs. Method handlers are similar, but the
    AST of the receiver (i.e. self) object is prepended as the first
    AST in the argument tuple. Handlers return the replacement tree,
    or None to skip the current match.
    """
    
    func_expr_pattern = (
        Call(Name(PatVar('_func'), Load()),
             PatVar('_args'),
             (), None, None))
    meth_expr_pattern = (
        Call(Attribute(PatVar('_self'), PatVar('_meth'), Load()),
             PatVar('_args'),
             (), None, None))
    func_stmt_pattern = Expr(func_expr_pattern)
    meth_stmt_pattern = Expr(meth_expr_pattern)
    
    def dispatch_func(self, _func, _args):
        """Dispatch to a fe or fs handler."""
        handler = getattr(self, 'handle_fe_' + _func, None)
        if handler is None:
            handler = getattr(self, 'handle_fs_' + _func, None)
        
        if handler is not None:
            return handler(_func, _args)
    
    def dispatch_meth(self, _self, _meth, _args):
        """Dispatch to a me or ms handler."""
        handler = getattr(self, 'handle_me_' + _meth, None)
        if handler is None:
            handler = getattr(self, 'handle_ms_' + _meth, None)
        
        if handler is not None:
            return handler(_meth, (_self,) + _args)
    
    def __init__(self):
        patrepls = [(self.func_expr_pattern, self.dispatch_func),
                    (self.func_stmt_pattern, self.dispatch_func),
                    (self.meth_expr_pattern, self.dispatch_meth),
                    (self.meth_stmt_pattern, self.dispatch_meth)]
        super().__init__(patrepls)


class Seq(AST):
    
    """Dummy node to temporarily represent tuples,
    since they get flattened by NodeTransformer.
    """
    
    _fields = ('elts',)

class SeqEliminator(NodeTransformer):
    
    """Replace Seq with actual tuples."""
    
    def visit_Seq(self, node):
        return node.elts

class PyMacroProcessor(MacroProcessor):
    
    """Provides fs and fe handlers for constructing statement and
    expression nodes from source text. This can be a convenient
    alternative to constructing an AST imperatively, or substituting
    placeholders with ASTs.
    """
    
    # Common helper for all nodes. Programmatically define handler
    # aliases for each node it is used with.
    def helper(self, name, args):
        return struct_nodes[name](*args)
    
    # Helper for producing tuples.
    def handle_fe_Seq(self, name, args):
        return Seq(args)
    
    def process(self, tree):
        tree = super().process(tree)
        tree = SeqEliminator.run(tree)
        return tree

for name, snode in struct_nodes.items():
    (base,) = snode.__bases__
    setattr(PyMacroProcessor, 'handle_fe_' + name,
            PyMacroProcessor.helper)

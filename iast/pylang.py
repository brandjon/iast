"""Templating system for substituting ASTs and creating AST macros."""


from inspect import signature, Parameter
from functools import partial, wraps

from simplestruct.type import checktype

from iast.node import (AST, struct_nodes, stmt, expr, Store,
                       Expr, Call, Name, Load, Attribute, Str, List, Tuple,
                       Attribute, Subscript, Starred, Module)
from iast.visitor import NodeTransformer
from iast.pattern import PatVar, PatternTransformer


__all__ = [
    'ContextSetter',
    'extract_mod',
    'NameExpander',
    'MacroProcessor',
    'PyMacroProcessor',
    'astargs',
]


class ContextSetter(NodeTransformer):
    
    """Propagate context type ctx to the appropriate nodes of an
    expression tree. Mirrors the behavior of set_context() in
    Python/ast.c. Specifically, nodes that have a context field
    get assigned a context of ctx, and Starred, List, and Tuple
    nodes also propagate ctx recursively.
    """
    
    def __init__(self, ctx):
        # Type, not instance.
        self.ctx = ctx
    
    def basic(self, node):
        return node._replace(ctx=self.ctx())
    
    def recur(self, node):
        node = self.generic_visit(node)
        node = node._replace(ctx=self.ctx())
        return node
    
    visit_Attribute = basic
    visit_Subscript = basic
    visit_Name = basic
    
    visit_Starred = recur
    visit_List = recur
    visit_Tuple = recur


def extract_mod(tree, mode=None):
    """Process a tree to extract a subtree of the top-level
    Module node. The part to return is selected by mode.
    
        mod:
          Return the original tree, unchanged. (default)
        
        code:
          Get the list of top-level statements.
        
        stmt_or_blank:
          The one top-level statement, or None if there are
          no statements.
        
        stmt:
          The one top-level statement.
        
        expr:
          The one top-level expression.
        
        lval:
          The one top-level expression, in Store context.
    """
    checktype(tree, Module)
    
    if mode == 'mod' or mode is None:
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
        
    elif mode in ['stmt', 'expr', 'lval']:
        if len(tree.body) != 1:
            raise ValueError('Mode "{}" requires exactly one statement '
                             '(got {})'.format(mode, len(tree.body)))
        tree = tree.body[0]
        if mode in ['expr', 'lval']:
            if not isinstance(tree, Expr):
                raise ValueError('Mode "{}" requires Expr node (got {})'
                                 .format(mode, type(tree).__name__))
            tree = tree.value
            
            if mode == 'lval':
                tree = ContextSetter.run(tree, Store)
    
    elif mode is not None:
        raise ValueError('Unknown parse mode "' + mode + '"')
    
    return tree


class NameExpander(NodeTransformer):
    
    """Replace names with ASTs according to the given mapping.
    Also allows replacing attribute names and function definition
    names, identified by special prefixes '@' and '<def>' in
    the mapping.
    """
    
    def __init__(self, subst):
        self.subst = subst
    
    def visit_Name(self, node):
        return self.subst.get(node.id, None)
    
    def visit_Attribute(self, node):
        node = self.generic_visit(node)
        new_attr = self.subst.get('@' + node.attr, None)
        if new_attr:
            node = node._replace(attr=new_attr)
        return node
    
    def visit_FunctionDef(self, node):
        node = self.generic_visit(node)
        new_name = self.subst.get('<def>' + node.name, None)
        if new_name:
            node = node._replace(name=new_name)
        return node


class MacroProcessor(PatternTransformer):
    
    """Visitor for substituting calls of specific functions and
    methods with arbitrary ASTs. Works in a bottom-up fashion.
    
    Four call patterns are supported: function expressions (fe),
    function statements (fs), method expressions (me), and method
    statements (ms). The function patterns match function calls where
    the function is syntactically identified by a Name node. They
    invoke the handler corresponding to that name. The method patterns
    have no syntactic restriction, and invoke the handler corresponding
    to the method name. The expression patterns match calls that occur
    anywhere, while the statement patterns only match calls that appear
    at statement level, i.e. inside an Expr node. All forms can accept
    keyword arguments, but not star args or double-star args.
    
    Handlers are defined as methods in MacroProcessor subclasses,
    similar to the visit_* methods in NodeVisitor subclasses. The
    method names have form
    
        handle_KIND_NAME
    
    where KIND is one of the four pattern types ("fe", etc.) and NAME
    is the function or method name to match.
    
    The handlers take in as the first argument (not counting "self")
    the function or method name. The remaining arguments are the ASTs
    of the arguments in the Call node. For methods, the first of these
    remaining arguments is the AST of the receiver of the method call.
    The handler returns an AST to replace the call with.
    
    For example, if the input AST contains an expression
    
        print(obj.foo(x + y, z=1))
    
    then we look for the handler handle_me_foo(). If it exists, it is
    called with positional arguments "foo", the AST for "obj", and the
    AST for "x + y"; and with keyword argument z = the AST for "1".
    If it returns the AST Num(5), our new tree is
    
        print(5)
    
    Note that a failure to match arguments will result in an exception,
    as if a Python function were called with the wrong signature.
    """
    
    func_expr_pattern = (
        Call(Name(PatVar('_func'), Load()),
             PatVar('_args'), PatVar('_keywords'),
             PatVar('_starargs'), PatVar('_kwargs')))
    meth_expr_pattern = (
        Call(Attribute(PatVar('_recv'), PatVar('_func'), Load()),
             PatVar('_args'), PatVar('_keywords'),
             PatVar('_starargs'), PatVar('_kwargs')))
    func_stmt_pattern = Expr(func_expr_pattern)
    meth_stmt_pattern = Expr(meth_expr_pattern)
    
    
    def dispatch(self, prefix, kind, *, _recv=None,
                 _func, _args, _keywords, _starargs, _kwargs):
        """Dispatch helper. prefix and kind are strings that vary based
        on the pattern form. _recv is prepended to _args if not None.
        """
        handler = getattr(self, prefix + _func, None)
        if handler is None:
            return
        
        if not (_starargs is None and _kwargs is None):
            raise TypeError('Star-args and double star-args are not '
                            'allowed in {} macro {}'.format(
                            kind, _func))
        
        if _recv is not None:
            _args = (_recv,) + _args
        _args = (_func,) + _args
        
        sig = signature(handler)
        ba = sig.bind(*_args, **{kw.arg: kw.value for kw in _keywords})
        return handler(*ba.args, **ba.kwargs)
    
    def __init__(self):
        patrepls = [
            (self.func_expr_pattern,
             partial(self.dispatch, prefix='handle_fe_', kind='function')),
            (self.func_stmt_pattern,
             partial(self.dispatch, prefix='handle_fs_', kind='function')),
            (self.meth_expr_pattern,
             partial(self.dispatch, prefix='handle_me_', kind='method')),
            (self.meth_stmt_pattern,
             partial(self.dispatch, prefix='handle_ms_', kind='method'))]
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
    def helper(self, name, *args, **kargs):
        return struct_nodes[name](*args, **kargs)
    
    # Helper for producing tuples.
    def handle_fe_Seq(self, name, *args):
        return Seq(args)
    
    def process(self, tree):
        tree = super().process(tree)
        tree = SeqEliminator.run(tree)
        return tree

for name, snode in struct_nodes.items():
    (base,) = snode.__bases__
    setattr(PyMacroProcessor, 'handle_fe_' + name,
            PyMacroProcessor.helper)


def astargs(func):
    """Decorator to automatically unwrap AST arguments."""
    sig = signature(func)
    @wraps(func)
    def f(*args, **kargs):
        ba = sig.bind(*args, **kargs)
        for name, val in ba.arguments.items():
            ann = sig.parameters[name].annotation
            
            if ann is Parameter.empty:
                pass
            
            elif ann == 'Str':
                checktype(val, Str)
                ba.arguments[name] = val.s
            
            elif ann == 'ids':
                if not (isinstance(val, (List, Tuple)) and
                        all(isinstance(e, Name) for e in val.elts)):
                    raise TypeError('Expected list of identifiers')
                ba.arguments[name] = tuple(v.id for v in val.elts)
        
        return func(*ba.args, **ba.kwargs)
    
    return f

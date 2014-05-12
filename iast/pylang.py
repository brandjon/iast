"""Templating system for substituting ASTs and creating AST macros."""


from inspect import signature, Parameter
from functools import partial, wraps, reduce
import operator
import itertools

from simplestruct.type import checktype

from iast.node import (AST, struct_nodes, stmt, expr, Store, With, withitem,
                       Expr, Call, Name, Load, Attribute, Str, List, Tuple,
                       Attribute, Subscript, Starred, Module, keyword, Num)
from iast.visitor import NodeVisitor, NodeTransformer
from iast.pattern import (PatVar, PatternTransformer,
                          instantiate_wildcards)


__all__ = [
    'ContextSetter',
    'extract_mod',
    'Templater',
    'literal_eval',
    'MacroProcessor',
    'PyMacroProcessor',
    'astargs',
]


# Taken from the documentation for the itertools module.
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


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


operator_map = {
    'And': lambda a, b: a and b,
    'Or': lambda a, b: a or b,
    
    'Add': operator.add,
    'Sub': operator.sub,
    'Mult': operator.mul,
    'Div': operator.truediv,
    'Mod': operator.mod,
    'Pow': operator.pow,
    'LShift': operator.lshift,
    'RShift': operator.rshift,
    'BitOr': operator.or_,
    'BitXor': operator.xor,
    'BitAnd': operator.and_,
    'FloorDiv': operator.floordiv,
    
    'Invert': operator.invert,
    'Not': operator.not_,
    'UAdd': operator.pos,
    'USub': operator.neg,
    
    'Eq': operator.eq,
    'NotEq': operator.ne,
    'Lt': operator.lt,
    'LtE': operator.le,
    'Gt': operator.gt,
    'GtE': operator.ge,
    'Is': operator.is_,
    'IsNot': operator.is_not,
    'In': operator.contains,
    'NotIn': lambda a, b: a not in b,
}

class LiteralEvaluator(NodeVisitor):
    
    """Helper for literal_eval."""
    
    name_map = {
        'None': None,
        'False': False,
        'True': True,
    }
    
    def seq_visit(self, seq):
        return seq
    
    def generic_visit(self, node):
        raise ValueError('Unsupported node ' + node.__class__.__name__)
    
    def visit_Num(self, node):
        return node.n
    
    def visit_Str(self, node):
        return node.s
    
    def visit_Bytes(self, node):
        return node.s
    
    def visit_Ellipsis(self, node):
        return Ellipsis
    
    def visit_Name(self, node):
        return self.name_map[node.id]
    
    def visit_Tuple(self, node):
        return tuple(self.visit(elt) for elt in node.elts)
    
    def visit_List(self, node):
        return list(self.visit(elt) for elt in node.elts)
    
    def visit_Set(self, node):
        return set(self.visit(elt) for elt in node.elts)
    
    def visit_Dict(self, node):
        return {self.visit(key): self.visit(value)
                for key, value in zip(node.keys, node.values)}
    
    def visit_BoolOp(self, node):
        func = operator_map[node.op.__class__.__name__]
        return reduce(func, (self.visit(value) for value in node.values))
    
    def visit_BinOp(self, node):
        func = operator_map[node.op.__class__.__name__]
        return func(self.visit(node.left), self.visit(node.right))
    
    def visit_UnaryOp(self, node):
        func = operator_map[node.op.__class__.__name__]
        return func(self.visit(node.operand))
    
    def visit_Compare(self, node):
        values = ((self.visit(node.left),) +
                  tuple(self.visit(c) for c in node.comparators))
        cmps = pairwise(values)
        return all(operator_map[op.__class__.__name__](a, b)
                   for ((a, b), op) in zip(cmps, node.ops))

def literal_eval(tree):
    """Analogous to ast.literal_eval(), with similar restrictions
    on the allowed types of nodes.
    """
    return LiteralEvaluator.run(tree)


class Templater(NodeTransformer):
    
    """Instantiate placeholders in the AST according to the given
    mapping. The following kinds of mappings are recognized. In
    all cases, the keys are strings.
    
        IDENT -> AST
          Replace Name occurrences for identifier IDENT with an
          arbitrary expression AST.
        
        IDENT1 -> IDENT2
          In Name occurrences, replace IDENT1 with IDENT2 while
          leaving context unchanged.
        
        IDENT -> func
          In Name occurrences, replace IDENT with the result of
          calling func(IDENT). The result may itself be an AST
          or identifier string, as above.
        
        @ATTR1 -> ATTR2
          Replace uses of attribute ATTR1 with ATTR2.
        
        <def>IDENT1 -> IDENT2
          In function definitions, replace the name of the defined
          function IDENT1 with IDENT2.
        
        <c>IDENT -> AST
          Replace Name occurrences of IDENT with an arbitrary
          code AST (i.e. tuple of statements).
    """
    
    def __init__(self, subst):
        self.subst = subst
    
    def name_helper(self, node, val):
        if isinstance(val, str):
            return node._replace(id=val)
        elif isinstance(val, AST):
            return val
        else:
            return self.name_helper(node, val(node.id))
    
    def visit_Name(self, node):
        repl = self.subst.get(node.id, None)
        if repl is not None:
            return self.name_helper(node, repl)
    
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
    
    def visit_Expr(self, node):
        if isinstance(node.value, Name):
            new_code = self.subst.get('<c>' + node.value.id)
            if new_code is not None:
                return new_code
        
        return self.generic_visit(node)


class MacroProcessor(PatternTransformer):
    
    """Visitor for substituting specific function and method calls
    with ASTs. Works in a bottom-up fashion.
    
    Several pattern forms are supported:
      - function expressions (fe)    "print(foo())"
      - function statements (fs)     "foo()"
      - method expressions (me)      "print(obj.foo())"
      - method statements (ms)       "obj.foo()"
      - function with (fw)           "with foo(): body"
      - method with (mw)             "with obj.foo(): body"
    
    The function patterns match function calls where the function is
    syntactically identified by a Name node. They invoke the handler
    corresponding to that name. The method patterns have no such
    syntactic restriction, and invoke the handler corresponding to the
    method name. The expression patterns match calls that occur
    anywhere, while the statement patterns only match calls that appear
    at statement level, i.e. inside an Expr node. All forms can accept
    keyword arguments, but not star args or double-star args.
    
    Handlers are defined as methods in MacroProcessor subclasses,
    similar to the visit_* methods in NodeVisitor subclasses. The
    method names have form
    
        handle_KIND_NAME
    
    where KIND is one of the six pattern types ("fe", etc.) and NAME
    is the function or method name to match.
    
    The handlers take in as the first argument (not counting "self")
    the function or method name. The remaining arguments are the ASTs
    of the arguments in the Call node. For methods, the first of these
    remaining arguments is the AST of the receiver of the method call.
    The with pattern handlers take an additional "_body" keyword
    argument. The handler returns an AST to replace the call with.
    
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
    
    func_with_pattern = With((withitem(func_expr_pattern, None),),
                             PatVar('_body'))
    meth_with_pattern = With((withitem(meth_expr_pattern, None),),
                             PatVar('_body'))
    
    
    def dispatch(self, prefix, kind, *, _recv=None, _body=None,
                 _func, _args, _keywords, _starargs, _kwargs):
        """Dispatch helper. prefix and kind are strings that vary based
        on the pattern form. _recv is prepended to _args if not None.
        If _body is not None, ('_body', _body) is added to _keywords.
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
        
        if _body is not None:
            _keywords += (keyword('_body', _body),)
        
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
             partial(self.dispatch, prefix='handle_ms_', kind='method')),
            (self.func_with_pattern,
             partial(self.dispatch, prefix='handle_fw_', kind='with')),
            (self.meth_with_pattern,
             partial(self.dispatch, prefix='handle_mw_', kind='with')),
        ]
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
    
    def __init__(self, patterns=False):
        super().__init__()
        self.patterns = patterns
    
    # Common helper for all nodes. Programmatically define handler
    # aliases for each node it is used with.
    def helper(self, name, *args, **kargs):
        nodecls = struct_nodes[name]
        if self.patterns:
            sig = nodecls._signature
            ba = sig.bind_partial(*args, **kargs)
            for param in sig.parameters:
                if param not in ba.arguments:
                    ba.arguments[param] = PatVar('_')
            args, kargs = ba.args, ba.kwargs
        
        return nodecls(*args, **kargs)
    
    # Helper for producing tuples.
    def handle_fe_Seq(self, name, *args):
        return Seq(args)
    
    def process(self, tree):
        tree = super().process(tree)
        tree = SeqEliminator.run(tree)
        if self.patterns:
            tree = instantiate_wildcards(tree)
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
            
            elif ann == 'Num':
                checktype(val, Num)
                ba.arguments[name] = val.n
            
            elif ann == 'Name':
                checktype(val, Name)
                ba.arguments[name] = val.id
            
            elif ann == 'ids':
                if not (isinstance(val, (List, Tuple)) and
                        all(isinstance(e, Name) for e in val.elts)):
                    raise TypeError('Expected list of identifiers')
                ba.arguments[name] = tuple(v.id for v in val.elts)
            
            else:
                raise TypeError('Unknown astarg specifier "{}"'.format(ann))
        
        return func(*ba.args, **ba.kwargs)
    
    return f

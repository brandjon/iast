"""Simple Python-specific AST utilities."""


# Names are exported using get_all() instead of __all__.
# This allows us to instantiate code with py33 or py34 ast
# types as needed.
__all__ = [
]


import sys
from functools import partial, reduce, wraps
import operator
from inspect import signature, Parameter
from simplestruct.type import checktype, checktype_seq

from ..util import pairwise
from ..visitor import NodeVisitor, NodeTransformer
from ..pattern import PatVar, Wildcard, PatternTransformer


def make_pattern(tree):
    """Make a pattern from an AST by replacing Name nodes with PatVars
    and Wildcards. Names beginning with an underscore are considered
    pattern vars. Names of '_' are considered wildcards.
    """
    class NameToPatVar(NodeTransformer):
        def visit_Name(self, node):
            if node.id == '_':
                return Wildcard()
            elif node.id.startswith('_'):
                return PatVar(node.id)
    
    return NameToPatVar.run(tree)


class ContextSetter(NodeTransformer):
    
    """Propagate context type ctx to the appropriate nodes of an
    expression tree. Mirrors the behavior of set_context() in
    the Python source tree file Python/ast.c. Specifically, nodes
    that have a context field get assigned a context of ctx, and
    Starred, List, and Tuple nodes also propagate ctx recursively.
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


def extract_tree(L, tree, mode=None):
    """Given a tree rooted at a Module node, return a subtree as
    selected by mode, which is one of the following strings.
    
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
    checktype(tree, L.Module)
    
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
            if not isinstance(tree, L.Expr):
                raise ValueError('Mode "{}" requires Expr node (got {})'
                                 .format(mode, type(tree).__name__))
            tree = tree.value
            
            if mode == 'lval':
                tree = ContextSetter.run(tree, L.Store)
    
    elif mode is not None:
        raise ValueError('Unknown parse mode "' + mode + '"')
    
    return tree


class LiteralEvaluator(NodeVisitor):
    
    """Analogous to ast.literal_eval(), with similar restrictions
    on the allowed types of nodes.
    """
    
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
        # This is used for the py33 grammar, which lacks NameConstant.
        map = {'True': True, 'False': False, 'None': None}
        if node.id not in map:
            raise ValueError("Unsupported Name node '{}'".format(node.id))
        return map[node.id]
    
    def visit_NameConstant(self, node):
        return node.value
    
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
        func = self.operator_map[node.op.__class__.__name__]
        return reduce(func, (self.visit(value) for value in node.values))
    
    def visit_BinOp(self, node):
        func = self.operator_map[node.op.__class__.__name__]
        return func(self.visit(node.left), self.visit(node.right))
    
    def visit_UnaryOp(self, node):
        func = self.operator_map[node.op.__class__.__name__]
        return func(self.visit(node.operand))
    
    def visit_Compare(self, node):
        values = ((self.visit(node.left),) +
                  tuple(self.visit(c) for c in node.comparators))
        cmps = pairwise(values)
        return all(self.operator_map[op.__class__.__name__](a, b)
                   for ((a, b), op) in zip(cmps, node.ops))


class Templater(NodeTransformer):
    
    """Instantiate placeholders in the AST according to the given
    mapping. The following kinds of mappings are recognized. In
    all cases, the keys are strings, and None values indicate
    "no change".
    
        IDENT -> AST
          Replace Name occurrences for identifier IDENT with an
          arbitrary non-None expression AST.
        
        IDENT1 -> IDENT2
          In Name occurrences, replace IDENT1 with IDENT2 while
          leaving context unchanged.
        
        @ATTR1 -> ATTR2
          Replace uses of attribute ATTR1 with ATTR2.
        
        <def>IDENT1 -> IDENT2
          In function definitions, replace the name of the defined
          function IDENT1 with IDENT2.
        
        <c>IDENT -> AST
          Replace Name occurrences of IDENT with an arbitrary
          code AST (i.e. tuple of statements).
    
    If the repeat flag is given, then the names and ASTs introduced
    by applying the mapping will be transformed repeatedly until
    no rules apply (or all applicable rules map to None). This means
    that a cyclic set of rules can cause an infinite loop. (This holds
    even if the rules apply but produce an equivalent tree.)
    
    If repeat is True, then bailout is the number of substitutions
    to allow before failing with an exception. Set bailout to None
    to disable this protection.
    """
    
    L = None
    """Stub for module reference."""
    
    def __init__(self, subst, *, repeat=False,
                 bailout=sys.getrecursionlimit()):
        super().__init__()
        self.subst = subst
        self.repeat = repeat
        self.bailout = bailout
    
    def fix(self, func, value):
        """If repeat is True, repeatedly apply func to value
        until a non-None result is obtained. Otherwise, apply
        func exactly once. In either case, return the last non-
        None value (or the original value if the first application
        was None).
        """
        steps = 0
        changed = True
        while changed:
            if steps >= self.bailout:
                raise RuntimeError('Exceeded bailout ({}) in '
                                   'Templater'.format(self.bailout))
            changed = False
            result = func(value)
            if result is not None:
                if self.repeat:
                    changed = True
                value = result
            steps += 1
        return value
    
    def visit_Name(self, node):
        def f(node):
            # If we yield a non-Name AST, stop.
            if not isinstance(node, self.L.Name):
                return None
            # Get the mapping entry for this identifier.
            # Result is either a string, None, or an expression AST.
            result = self.subst.get(node.id, None)
            # Normalize string to Name node.
            if isinstance(result, str):
                result = node._replace(id=result)
            return result
        
        return self.fix(f, node)
    
    def visit_Attribute(self, node):
        # Recurse first. If we repeatedly change the attribute
        # name in the fixpoint loop, the node's subexpressions
        # won't be affected.
        node = self.generic_visit(node)
        
        def f(node):
            new_attr = self.subst.get('@' + node.attr, None)
            if new_attr is None:
                return None
            else:
                return node._replace(attr=new_attr)
        
        return self.fix(f, node)
    
    def visit_FunctionDef(self, node):
        # Recurse first, as above.
        node = self.generic_visit(node)
        
        def f(node):
            new_name = self.subst.get('<def>' + node.name, None)
            if new_name is None:
                return None
            else:
                return node._replace(name=new_name)
        
        return self.fix(f, node)
    
    def visit_Expr(self, node):
        # Don't recurse first. We want a '<c>Foo' rule to take
        # precedence over a 'Foo' rule.
        #
        # Don't use self.fix. If we repeat, we want to recursively
        # apply arbitrary rules to the new substitution result.
        if isinstance(node.value, self.L.Name):
            new_code = self.subst.get('<c>' + node.value.id, None)
            if new_code is not None:
                if self.repeat:
                    # Note that we visit(), not generic_visit(),
                    # so rules can apply freely at the top level
                    # of new_code.
                    new_code = self.visit(new_code)
                return new_code
        
        # If the rule didn't trigger or it said no change,
        # process subtree as normal.
        node = self.generic_visit(node)
        return node


def astargs(L, func):
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
                checktype(val, L.Str)
                ba.arguments[name] = val.s
            
            elif ann == 'Num':
                checktype(val, L.Num)
                ba.arguments[name] = val.n
            
            elif ann == 'Name':
                checktype(val, L.Name)
                ba.arguments[name] = val.id
            
            elif ann == 'List':
                checktype(val, L.List)
                ba.arguments[name] = val.elts
            
            elif ann == 'ids':
                if not isinstance(val, (L.List, L.Tuple)):
                    raise TypeError('Expected List or Tuple node')
                checktype_seq(val.elts, L.Name)
                ba.arguments[name] = tuple(v.id for v in val.elts)
            
            else:
                raise TypeError('Unknown astarg specifier "{}"'.format(ann))
        
        return func(*ba.args, **ba.kwargs)
    
    return f


class MacroProcessor(PatternTransformer):
    
    """Framework for substituting uses of specific functions and
    methods with arbitrary ASTs. Each substitution is handled
    innermost-first. If repeat is given, the substituted AST
    is also transformed.
    
    The following kinds of uses are supported:
    
      - function expressions (fe)    "print(foo())"
      - function statements (fs)     "foo()"
      - method expressions (me)      "print(obj.foo())"
      - method statements (ms)       "obj.foo()"
      - function with (fw)           "with foo(): body"
      - method with (mw)             "with obj.foo(): body"
    
    The expression patterns match calls that occur anywhere, while the
    statement patterns only match calls that appear at statement level,
    i.e. immediately inside an Expr node.
    
    Function and method patterns invoke the handler whose name
    corresponds to the syntactic name appearing in the call AST.
    For methods, this is just the attribute identifier on the method
    call. For functions, the pattern only matches when the function
    is given by a Name node, not an arbitrary expression. If the same
    name is used for multiple kinds of handlers, expression handlers
    take precedence over statement and with handlers, since the rules
    are applied to innermost matches first.
    
    All forms can accept keyword arguments, but not variadic arguments
    (*args and **kargs).
    
    Handlers are defined as methods in MacroProcessor subclasses,
    similar to the visit_* methods in NodeVisitor subclasses. The
    method names have form
    
        handle_KIND_NAME
    
    where KIND is the abbreviation for one of the six pattern types
    ("fe", etc.) and NAME is the syntactic function or method name to
    match.
    
    The handlers take in as the first argument (not counting "self")
    the function or method name that the pattern matched. (This allows
    the same handler to be reused under multiple names.) The remaining
    arguments are the ASTs of the arguments in the Call node. For
    methods, the first of these remaining arguments is the AST of the
    receiver of the method call (i.e. the expression to the left of the
    dot). If the Call node has keyword arguments, these are passed as
    keywords from the key to the AST of the argument value. The "with"
    pattern handlers take an additional '_body' keyword argument, bound
    to the AST (tuple of statements) of the with body.
    
    The handlers return an AST to replace the matched tree with.
    A return value of None indicates no change.
    
    For example, if the input AST contains an expression
    
        print(obj.foo(x + y, z=1))
    
    then we look for the handler 'handle_me_foo()'. If it exists, it is
    called with positional arguments "foo", the AST for "obj", and the
    AST for "x + y"; and with keyword argument z = the AST for "1".
    If it returns the AST Num(5), our new tree is
    
        print(5)
    
    Note that a failure to match the arguments in a Call with the
    arguments of the handler will result in an exception, the same
    as when a Python function is called with the wrong signature.
    """
    
    L = None
    """Stub for module reference."""
    
    @property
    def func_expr_pattern(self):
        L = self.L
        return L.Call(L.Name(PatVar('_func'), L.Load()),
                      PatVar('_args'), PatVar('_keywords'),
                      PatVar('_starargs'), PatVar('_kwargs'))
    
    @property
    def meth_expr_pattern(self):
        L = self.L
        return L.Call(L.Attribute(PatVar('_recv'), PatVar('_func'),
                                  L.Load()),
                      PatVar('_args'), PatVar('_keywords'),
                      PatVar('_starargs'), PatVar('_kwargs'))
    
    @property
    def func_stmt_pattern(self):
        L = self.L
        return L.Expr(self.func_expr_pattern)
    
    @property
    def meth_stmt_pattern(self):
        L = self.L
        return L.Expr(self.meth_expr_pattern)
    
    @property
    def func_with_pattern(self):
        L = self.L
        return L.With((L.withitem(self.func_expr_pattern, None),),
                      PatVar('_body'))
    
    @property
    def meth_with_pattern(self):
        L = self.L
        return L.With((L.withitem(self.meth_expr_pattern, None),),
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
        
        kwargs = {kw.arg: kw.value for kw in _keywords}
        if _body is not None:
            kwargs['_body'] = _body
        
        sig = signature(handler)
        ba = sig.bind(*_args, **kwargs)
        return handler(*ba.args, **ba.kwargs)
    
    def __init__(self):
        super().__init__()
        self.rules = [
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


def get_all(module):
    class _Templater(Templater):
        L = module 
    class _MacroProcessor(MacroProcessor):
        L = module
    
    return {
        'make_pattern': make_pattern,
        'ContextSetter': ContextSetter,
        'extract_tree': partial(extract_tree, module),
        'LiteralEvaluator': LiteralEvaluator,
        'literal_eval': LiteralEvaluator().process,
        'Templater': _Templater,
        'astargs': partial(astargs, module),
        'MacroProcessor': _MacroProcessor,
    }

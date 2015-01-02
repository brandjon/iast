"""Templating system for substituting ASTs and creating AST macros."""


__all__ = [
    'MacroProcessor',
    'astargs',
]


from inspect import signature, Parameter
from functools import partial, wraps, reduce
import operator
import itertools
from simplestruct.type import checktype

from .node import AST
from .pynode import (nodes, stmt, expr, Store, With, withitem,
                     Expr, Call, Name, Load, Attribute, Str, List, Tuple,
                     Attribute, Subscript, Starred, Module, keyword, Num)
from .visitor import NodeVisitor, NodeTransformer
from .pattern import (PatVar, PatternTransformer,
                      instantiate_wildcards)







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
        
        kwargs = {kw.arg: kw.value for kw in _keywords}
        if _body is not None:
            kwargs['_body'] = _body
        
        sig = signature(handler)
        ba = sig.bind(*_args, **kwargs)
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
            
            elif ann == 'List':
                checktype(val, List)
                ba.arguments[name] = val.elts
            
            elif ann == 'ids':
                if not (isinstance(val, (List, Tuple)) and
                        all(isinstance(e, Name) for e in val.elts)):
                    raise TypeError('Expected list of identifiers')
                ba.arguments[name] = tuple(v.id for v in val.elts)
            
            else:
                raise TypeError('Unknown astarg specifier "{}"'.format(ann))
        
        return func(*ba.args, **ba.kwargs)
    
    return f

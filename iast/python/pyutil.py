"""Simple Python-specific AST utilities."""


# Names are exported using get_all() instead of __all__.
# This allows us to instantiate code with py33 or py34 ast
# types as needed.
__all__ = [
]


import sys
from functools import partial, reduce
import operator
from simplestruct.type import checktype, checktype_seq

from ..util import pairwise
from ..visitor import NodeVisitor, NodeTransformer
from ..pattern import PatVar, Wildcard


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


def get_all(module):
    class _Templater(Templater):
        L = module 
    
    return {
        'make_pattern': make_pattern,
        'ContextSetter': ContextSetter,
        'extract_tree': partial(extract_tree, module),
        'LiteralEvaluator': LiteralEvaluator,
        'literal_eval': LiteralEvaluator().process,
        'Templater': _Templater,
    }

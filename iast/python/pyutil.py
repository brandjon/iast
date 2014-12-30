"""Simple Python-specific AST utilities."""


__all__ = [
]


from functools import partial, reduce
import operator
from simplestruct.type import checktype, checktype_seq

from ..util import pairwise
from ..visitor import NodeVisitor, NodeTransformer


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


def get_all(L):
    return {
        'ContextSetter': ContextSetter,
        'extract_tree': partial(extract_tree, L),
        'LiteralEvaluator': LiteralEvaluator,
        'literal_eval': LiteralEvaluator().process
    }

"""Pattern-matching and unificaiton for struct ASTs"""


import ast

from iast.node import AST
from iast.visitor import NodeVisitor, NodeTransformer


__all__ = [
    'MatchFailure',
    'PatMaker',
    'unify_eqs',
]


class MatchFailure(Exception):
    """Raised on unification failure, to exit the recursion."""


class pattern(AST):    
    """Meta node for AST patterns."""

class PatVar(pattern):
    
    """Pattern variable."""
    
    _fields = ('id',)


class PatMaker(NodeTransformer):
    
    """Make a pattern from an AST by replacing Name nodes with PatVars.
    Names that begin with an underscore are considered pattern vars.
    """
    
    def visit_Name(self, node):
        if node.id.startswith('_'):
            return PatVar(node.id)

class VarExpander(NodeTransformer):
    
    """Expand pattern variables."""
    
    def __init__(self, var, repl):
        self.var = var
        self.repl = repl
    
    def visit_PatVar(self, node):
        if node.id == self.var:
            return self.repl

class OccChecker(NodeVisitor):
    
    """Run an occurs-check."""
    
    def __init__(self, var):
        self.var = var
    
    def process(self, tree):
        self.found = False
        super().process(tree)
        return self.found
    
    def visit_PatVar(self, node):
        if node.id == self.var:
            self.found = True


def unify_eqs(eqs):
    """Given a list of equations, run the unification algorithm.
    Return a mapping from each variable to a tree, where the variable
    does not appear anywhere else in the mapping.
    """
    result = {}
    def bindvar(var, repl):
        """Add a binding var -> repl. Replace var with repl in the
        equations list and in the other result mappings.
        """
        result[var] = repl
        trans = VarExpander(var, repl)
        for k in result:
            result[k] = trans.process(result[k])
        for i, (lhs, rhs) in enumerate(eqs):
            eqs[i] = (trans.process(lhs), trans.process(rhs))
    
    while len(eqs) > 0:
        lhs, rhs = eqs.pop()
        # Flip for symmetric case.
        if not isinstance(lhs, PatVar) and isinstance(rhs, PatVar):
            lhs, rhs = rhs, lhs
        
        # <variable> matching <anything>
        if isinstance(lhs, PatVar):
            if not (isinstance(rhs, PatVar) and rhs.id == lhs.id):
                if OccChecker.run(rhs, lhs.id):
                    raise MatchFailure('Circular match on ' + lhs.id)
                bindvar(lhs.id, rhs)
        
        # <node functor> matching <non-variable>
        elif isinstance(lhs, AST):
            if not isinstance(rhs, AST):
                raise MatchFailure(
                    'Node {} does not match non-node {}'.format(
                    lhs.__class__.__name__, repr(rhs)))
            elif not type(lhs) == type(rhs):
                raise MatchFailure('Node {} does not match node {}'.format(
                                   lhs.__class__.__name__,
                                   rhs.__class__.__name__))
            else:
                for field in lhs._fields:
                    eqs.append((getattr(lhs, field), getattr(rhs, field)))
        
        # <tuple functor> matching <non-variable>
        elif isinstance(lhs, tuple):
            if not isinstance(rhs, tuple):
                raise MatchFailure(
                    'Sequence {} does not match non-sequence {}'.format(
                    repr(lhs), repr(rhs)))
            elif len(lhs) != len(rhs):
                raise MatchFailure(
                    'Sequence {} and sequence {} have '
                    'different lengths'.format(
                    repr(lhs), repr(rhs)))
            else:
                for item1, item2 in zip(lhs, rhs):
                    eqs.append((item1, item2))
        
        # <constant> matching <non-variable>
        else:
            if lhs != rhs:
                raise MatchFailure(
                    'Constant {} does not match {}'.format(
                    repr(lhs), repr(rhs)))
    
    return result

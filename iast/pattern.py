"""Pattern-matching and unificaiton for struct ASTs"""


import ast

from iast.node import AST
from iast.visitor import NodeVisitor, NodeTransformer


__all__ = [
    'MatchFailure',
    'PatVar',
    'PatMaker',
    'match',
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


def match_step(lhs, rhs):
    """Attempt to match lhs against rhs at the top-level. Return a
    list of equations that must hold for the matching to succeed,
    or raise MatchFailure if matching is not possible. Variable
    bindings are also returned, as a mapping.
    """
    # In practice, bindings is always either empty or contains
    # just one mapping.
    bindings = {}
    
    # Flip for symmetric case.
    if not isinstance(lhs, PatVar) and isinstance(rhs, PatVar):
        lhs, rhs = rhs, lhs
    
    # <variable> matching <anything>
    if isinstance(lhs, PatVar):
        eqs = []
        if not (isinstance(rhs, PatVar) and rhs.id == lhs.id):
            if OccChecker.run(rhs, lhs.id):
                raise MatchFailure('Circular match on ' + lhs.id)
            bindings[lhs.id] = rhs
    
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
            eqs = [(getattr(lhs, field), getattr(rhs, field))
                   for field in lhs._fields]
    
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
            eqs = list(zip(lhs, rhs))
    
    # <constant> matching <non-variable>
    else:
        if lhs != rhs:
            raise MatchFailure(
                'Constant {} does not match {}'.format(
                repr(lhs), repr(rhs)))
        eqs = []
    
    return eqs, bindings


def match(tree1, tree2):
    """Given two trees to match, run the unification algorithm. Return
    a mapping from each variable to a tree, where the variable does not
    appear anywhere else in the mapping.
    """
    eqs = [(tree1, tree2)]
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
        new_eqs, new_bindings = match_step(lhs, rhs)
        eqs.extend(new_eqs)
        for var, repl in new_bindings.items():
            bindvar(var, repl)
    
    return result

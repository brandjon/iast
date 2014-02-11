"""Pattern-matching and unification for struct ASTs."""

# IDEA: Could exploit the fact that Python expressions never contain
# statements, to avoid descending into expressions when trying to
# match a statement.


import itertools

from iast.node import AST
from iast.visitor import NodeVisitor, NodeTransformer


__all__ = [
    'MatchFailure',
    'PatVar',
    'PatMaker',
    'raw_match',
    'match',
    'sub',
    'PatternTransformer',
]


class MatchFailure(Exception):
    """Raised on unification failure, to exit the recursion."""


class pattern(AST):    
    """Meta node for AST patterns."""

class PatVar(pattern):
    
    """Pattern variable."""
    
    _fields = ('id',)

def is_wildname(id):
    # Wildcards begin with two underscores.
    return id.startswith('__')


class PatMaker(NodeTransformer):
    
    """Make a pattern from an AST by replacing Name nodes with PatVars.
    Names that begin with an underscore are considered pattern vars.
    """
    
    def __init__(self):
        self.wildname = ('__' + str(i) for i in itertools.count())
    
    def visit_Name(self, node):
        if node.id == '_':
            return PatVar(next(self.wildname))
        elif node.id.startswith('_'):
            return PatVar(node.id)

class VarExpander(NodeTransformer):
    
    """Expand pattern variables."""
    
    def __init__(self, mapping):
        self.mapping = mapping
    
    def visit_PatVar(self, node):
        return self.mapping.get(node.id, None)

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


def raw_match(tree1, tree2):
    """Given two trees to match, run the unification algorithm. Return
    a mapping from each variable to a tree, where the variable does not
    appear anywhere else in the mapping. Raise MatchFailure on failure.
    """
    eqs = [(tree1, tree2)]
    result = {}
    
    def bindvar(var, repl):
        """Add a binding var -> repl. Replace var with repl in the
        equations list and in the other result mappings.
        """
        result[var] = repl
        trans = VarExpander({var: repl})
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
    
    # Remove wildcard bindings.
    for k in list(result.keys()):
        if is_wildname(k):
            del result[k]
    
    return result

def match(tree1, tree2):
    """Same as raw_match(), but return None instead of raising
    MatchFailure.
    """
    try:
        return raw_match(tree1, tree2)
    except MatchFailure:
        return None 


# Pattern substitution takes in a pattern tree P with variables X,
# and an input tree T. If P matches T, a new tree is returned as
# determined by a replacement function (repl). The repl takes in
# each X as a keyword argument, bound to the corresponding matching
# subtree of T. As a convenience, the repl may be given instead as
# an AST that contains uses of the vars in X. The repl returns
# either a replacement tree, or None to skip this match.


def normalize_repl(repl):
    """Turn AST repls into function repls."""
    if isinstance(repl, AST):
        return lambda **mapping: VarExpander.run(repl, mapping)
    else:
        return repl

class Substitutor(NodeTransformer):
    
    """Perform pattern substitution on all outermost matching subtrees."""
    
    def __init__(self, pattern, repl):
        self.pattern = pattern
        self.repl = normalize_repl(repl)
    
    def visit(self, tree):
        mapping = match(self.pattern, tree)
        if mapping is not None:
            # Match. If repl returns None, continue recursing.
            result = self.repl(**mapping)
            if result is None:
                result = super().visit(tree)
            return result
        else:
            return super().visit(tree)

def sub(pattern, repl, tree):
    """Analogous to re.sub(). All outermost occurrences of pattern in
    tree are replaced according to repl.
    """
    return Substitutor.run(tree, pattern, repl)


class PatternTransformer(NodeTransformer):
    
    """Apply multiple patterns, bottom-up. Accepts a list of
    (pattern, repl) pairs, and applies each one in turn until the
    pattern matches and the repl returns a non-None value. Children
    are processed before the current node is matched against.
    """
    
    def __init__(self, patrepls):
        self.patrepls = [(pattern, normalize_repl(repl))
                         for pattern, repl in patrepls]
    
    def visit(self, tree):
        subresult = super().visit(tree)
        if subresult is not None:
            tree = subresult
        
        for pattern, repl in self.patrepls:
            mapping = match(pattern, tree)
            if mapping is not None:
                patresult = repl(**mapping)
                if patresult is not None:
                    return patresult
        
        # No patterns matched. Propagate the (possibly None) subresult.
        return subresult

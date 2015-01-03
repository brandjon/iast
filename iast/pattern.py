"""Pattern-matching for Struct ASTs."""


__all__ = [
    'MatchFailure',
    'pattern',
    'PatVar',
    'Wildcard',
    'raw_match',
    'match',
    'PatternTransformer',
]


from .node import AST
from .visitor import NodeVisitor, NodeTransformer


class MatchFailure(Exception):
    """Raised on unification failure, to exit the recursion."""


class pattern(AST):
    """Pattern term."""
    _meta = True

class PatVar(pattern):
    """Pattern variable."""
    _fields = ('id',)

class Wildcard(pattern):
    """Wildcard pattern variable."""
    _fields = ()


class VarExpander(NodeTransformer):
    
    """Expand pattern variables."""
    
    def __init__(self, mapping):
        super().__init__()
        self.mapping = mapping
    
    def visit_PatVar(self, node):
        return self.mapping.get(node.id, node)

class OccChecker(NodeVisitor):
    
    """Run an occurs-check for a variable."""
    
    class Found(Exception):
        pass
    
    def __init__(self, var):
        super().__init__()
        self.var = var
    
    def process(self, tree):
        try:
            super().process(tree)
        except self.Found:
            return True
        else:
            return False
    
    def visit_PatVar(self, node):
        if node.id == self.var:
            raise self.Found


def match_step(lhs, rhs):
    """Attempt to match lhs against rhs at the top-level. Return a
    list of equations that must hold for the matching to succeed,
    or raise MatchFailure if matching is not possible. Variable
    bindings are also returned, as a mapping.
    """
    # Ignore wildcards.
    if isinstance(lhs, Wildcard) or isinstance(rhs, Wildcard):
        return [], {}
    
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
    
    return result

def match(tree1, tree2):
    """Same as raw_match(), but return None instead of raising
    MatchFailure.
    """
    try:
        return raw_match(tree1, tree2)
    except MatchFailure:
        return None


class PatternTransformer(NodeTransformer):
    
    """Apply pattern substitution rules in a bottom-up (post-traversal)
    manner.
    
    A rule consists of a pattern tree and a replacement function.
    When a rule is applied to an input tree, if the pattern matches
    the input, then the tree gets replaced by the result of calling
    the function. The function is passed keyword arguments for each
    of the pattern's PatVars, bound to the corresponding matching
    subtree of the input.
    
    The replacement function may return NotImplemented to defer to
    subsequent rules. None may be returned to indicate "no change"
    (but see NodeTransformer for information on the _nochange_none
    flag).
    
    As a convenience, a rule may give an AST instead of a replacement
    function. The AST serves as a template where PatVars get expanded
    according to the match.
    """
    
    def normalize_repl_func(self, repl):
        """Normalize a value that is either a replacement function
        or an AST to just a replacement function.
        """
        if isinstance(repl, AST):
            return lambda **mapping: VarExpander.run(repl, mapping)
        else:
            return repl
    
    rules = []
    """List of rules to apply, in order of precedence. Each rule
    is a pair of a pattern tree and a replacement function (or
    AST).
    """
    
    def visit(self, tree):
        # Process subtree first.
        subtree_result = super().visit(tree)
        
        for pattern, repl in self.rules:
            mapping = match(pattern, subtree_result)
            if mapping is not None:
                # If the match succeeded, consult the repl.
                repl_result = repl(**mapping)
                if repl_result is NotImplemented:
                    # Defer to next rule.
                    continue
                if (self._nochange_none and
                    isinstance(tree, AST) and repl_result is None):
                    # Normalize None.
                    repl_result = subtree_result
                return repl_result
        else:
            # No matching rule found.
            return subtree_result

"""Python-specific pattern-matching helpers."""


__all__ = [
    'instantiate_wildcards',
    'make_pattern',
]


import itertools

from .visitor import NodeVisitor, NodeTransformer
from .pattern import PatVar


def is_wildname(id):
    # Wildcards begin with two underscores.
    return id.startswith('__')


def instantiate_wildcards(tree):
    """Turn each occurrence of a wildcard PatVar into a uniquely-named
    PatVar.
    """
    # We take care not to clash with an existing PatVar name
    # (e.g. from a previously instantiated wildcard).
    wildnames = ('__' + str(i) for i in itertools.count())
    
    class PatVarFinder(NodeVisitor):
        def process(self, tree):
            self.ids = set()
            super().process(tree)
            return self.ids
        def visit_PatVar(self, node):
            self.ids.add(node.id)
    
    used = PatVarFinder.run(tree)
    
    class WildcardInstantiator(NodeTransformer):
        def visit_PatVar(self, node):
            if node.id == '_':
                name = next(wildnames)
                while name in used:
                    name = next(wildnames)
                return node._replace(id=name)
    
    tree = WildcardInstantiator.run(tree)
    return tree


def make_pattern(tree):
    """Make a pattern from an AST by replacing Name nodes with PatVars.
    Names that begin with an underscore are considered pattern vars.
    Names of '_' are considered wildcards.
    """
    
    class NameToPatVar(NodeTransformer):
        def visit_Name(self, node):
            if node.id.startswith('_'):
                return PatVar(node.id)
    
    tree = NameToPatVar.run(tree)
    tree = instantiate_wildcards(tree)
    return tree

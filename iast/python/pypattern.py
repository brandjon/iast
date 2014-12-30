"""Python-specific pattern-matching helpers."""


__all__ = [
    'make_pattern',
]


from ..visitor import NodeTransformer
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

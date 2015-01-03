"""Example using an abstract grammar for a simple toy language.
Demonstrates structural properties, type checking, and differences
with Python's own ast module.
"""

import iast
import ast

# Generate the nodes from ASDL.
# Note the flags passed to nodes_from_asdl():
#
# - typed=True makes the node classes type-checked to enforce that their
#   children conform to the grammar in the ASDL.
#
# - module=__name__ explicitly sets this module as the defining module
#   for the node classes. This helps ensure that node instances can be
#   pickled, although it should still work so long as this module is
#   accessible via sys.modules.
#
with open('toy.asdl', 'rt') as file:
    absgrammar = iast.parse_asdl(file.read())
lang = iast.node.nodes_from_asdl(absgrammar, typed=True, module=__name__)
globals().update(lang)


# iAST node classes are subclasses of simplestruct.Struct, and
# therefore have structural equality.
node1 = Num(5)
node2 = Num(5)
print(node1 is node2)   # False
print(node1 == node2)   # True

# Compare this to Python's ast library.
node1 = ast.Num(5)
node2 = ast.Num(5)
print(node1 is node2)   # False
print(node1 == node2)   # False

# iAST nodes are immutable and hashable.
node1 = Num(5)
node2 = Num(5)
try:
    node1.n = 6
except AttributeError as e:
    print(e)            # Struct is immutable
print(hash(node1))      # The hash values must be the same
print(hash(node2))      # since they are equal.

# Python's ast library's nodes are mutable. This can give it
# a speed advantage for tree transformations (the fact that
# they're implemented in C also helps). Personally, I find
# mutability in tree transformations to be more error-prone.
#
# Python ast nodes are hashable, but without structural equality,
# hashes aren't very useful. For instance, if you want to test
# whether the AST for some expression is in a set, you need to
# already have a reference to that AST -- essentially the interned
# representation for that expression. It's not enough to parse the
# expression and make a new AST.

# iAST nodes are (optionally) type-checked.
try:
    Var(5)
except TypeError as e:
    print(e)            # Error constructing Var (field 'id'):
                        # Expected str; got int

# Child fields marked ? in the ASLD are optionally None.
# They still must be explicitly passed to the constructor.
Print(Num(5))
Print(None)

# Child fields marked * are sequence valued. They can be
# tuples or lists (normalized to tuples).
program([Pass(), Pass()])
try:
    program(Pass())
except TypeError as e:
    print(e)            # Error constructing program (field 'code'):
                        # Expected sequence of stmt; got Pass node instead

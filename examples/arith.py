"""Example of a simple language of arithmetic expressions.
Demonstrates parsing ASDL to create node classes, and using
visitors and transformers to process the tree.
"""

import iast

# Read and parse the abstract grammar from an ASDL file.
with open('arith.asdl', 'rt') as file:
    absgrammar = iast.parse_asdl(file.read())
# Generate node classes and store them in a mapping by name.
lang = iast.node.nodes_from_asdl(absgrammar)
# Flood the global namespace with these node classes so
# we can use them more easily.
globals().update(lang)


class Unparser(iast.NodeVisitor):
    
    """Turns AST back into an expression string."""
    
    def process(self, tree):
        self.tokens = []
        super().process(tree)
        return ''.join(self.tokens)
    
    def visit_BinOp(self, node):
        self.tokens.append('(')
        self.visit(node.left)
        self.tokens.append(' ')
        self.visit(node.op)
        self.tokens.append(' ')
        self.visit(node.right)
        self.tokens.append(')')
    
    def visit_Neg(self, node):
        self.tokens.append('-(')
        self.visit(node.value)
        self.tokens.append(')')
    
    def visit_Num(self, node):
        self.tokens.append(str(node.n))
    
    def visit_Var(self, node):
        self.tokens.append(node.id)
    
    def op_helper(self, node):
        map = {'Add': '+', 'Sub': '-', 'Mult': '*', 'Div': '/'}
        self.tokens.append(map[node.__class__.__name__])
    
    visit_Add = visit_Sub = visit_Mult = visit_Div = op_helper


class Simplifier(iast.NodeTransformer):
    
    """Constructs a simplified AST based on a few rewriting rules."""
    
    def visit_Neg(self, node):
        # Process the expression being negated first.
        node = self.generic_visit(node)
        
        # If the inside value is also a Neg, we cancel out.
        if isinstance(node.value, Neg):
            return node.value.value
        # If the inside value is zero, Neg is redundant.
        # (Note the use of structural equality on node instances.)
        elif node.value == Num(0):
            return Num(0)
        # Oh well. Be sure to return node. Returning None indicates
        # "no change", which would mean ignoring any rewriting done
        # to the inner expression by generic_visit() above.
        else:
            return node
    
    def visit_BinOp(self, node):
        # Process operand expressions first.
        node = self.generic_visit(node)
        
        # Zero-times-anything rule.
        if (node.op == Mult() and
            (node.left == Num(0) or node.right == Num(0))):
            # Return the AST to replace this node.
            return Num(0)
        # Zero-plus-anything rule.
        elif (node.op == Add() and
              (node.left == Num(0) or node.right == Num(0))):
            return node.right if node.left == Num(0) else node.left
        else:
            return node


tree = (BinOp(BinOp(BinOp(Var('x'), Add(), Num(3)), Mult(), Neg(Num(0))),
              Add(),
              BinOp(Var('x'), Sub(), Neg(Neg(Num(2))))))
# This works because we flooded the global namespace. If we didn't do
# that, we could have instead accessed nodes in lang by their name
# (lang['BinOp'], etc.), or we could have used eval() with lang as
# the namespace, as in:
#
#    tree = eval("BinOp(Var('x'), Add(), Num(3))", lang)

# ASTs get a straightforward repr() from simplestruct.
print(tree)
print()

# We can also use a multi-line pretty printer.
print(iast.dump(tree))
print()

# Visitors can be used by instantiating them and calling the
# process() method with the tree as the argument. As a shorthand,
# the classmethod run() does both instantiation and calling process().
print(Unparser.run(tree))
print()

# For transformers, the result is a new tree. Be sure to use
# assignment to overwrite the old tree.
tree = Simplifier.run(tree)
print(Unparser.run(tree))

"""Unit tests for node.py."""


import unittest

from simplestruct import Field

from iast.util import trim
from iast.node import *


class NodeCase(unittest.TestCase):
    
    def test_node(self):
        # Define, construct, and repr.
        class Foo(AST):
            _fields = ('a', 'b', 'c')
            b = Field()
        node = Foo(1, 2, 3)
        s = repr(node)
        exp_s = 'Foo(a=1, b=2, c=3)'
        self.assertEqual(s, exp_s)
        
        # Reconstruct the tree from repr.
        node2 = eval(s, locals())
        self.assertEqual(node2, node)
    
    def test_dump(self):
        class Add(AST):
            _fields = ['left', 'right']
        class Sum(AST):
            _fields = ['operands']
        tree = Sum((Add(1, 2), Sum((3, 4,)), Sum((5,)), Sum(()),))
        s = dump(tree)
        exp_s = trim('''\
            Sum(operands = (Add(left = 1,
                                right = 2),
                            Sum(operands = (3,
                                            4)),
                            Sum(operands = (5,)),
                            Sum(operands = ())))
            ''')
        self.assertEqual(s, exp_s)
        
        # Reconstruct the tree from dump.
        tree2 = eval(s, locals())
        self.assertEqual(tree2, tree)


if __name__ == '__main__':
    unittest.main()

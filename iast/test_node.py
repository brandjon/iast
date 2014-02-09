"""Unit tests for node.py."""


import unittest
import ast

from simplestruct import Struct

from iast.node import *


class NodeCase(unittest.TestCase):
    
    def testNode(self):
        node = Name('a', Load())
        self.assertEqual(str(node), 'Name(id=a, ctx=Load())')
    
    def testImport(self):
        tree = ast.parse('a')
        new_tree = pyToStruct(tree)
        exp_str = "Module(body=[Expr(value=Name(id='a', ctx=Load()))])"
        self.assertTrue(isinstance(new_tree, Struct))
        self.assertEqual(str(new_tree), exp_str)


if __name__ == '__main__':
    unittest.main()

"""Unit tests for pynode.py."""


import unittest
import ast

from iast.node import AST
from iast.pynode import *


class NodeCase(unittest.TestCase):
    
    tree_str = "Module(body=(Expr(value=Name(id='a', ctx=Load())),))"
    
    def test_init_nodetypes(self):
        node = Name('a', Load())
        self.assertEqual(repr(node), "Name(id='a', ctx=Load())")
        self.assertEqual(Name.__bases__, (expr,))
    
    def test_import(self):
        tree = ast.parse('a')
        tree = pyToStruct(tree)
        self.assertTrue(isinstance(tree, AST))
        self.assertEqual(str(tree), self.tree_str)
    
    def test_export(self):
        tree = eval(self.tree_str, nodes)
        tree = structToPy(tree)
        exp_str = "Module(body=[Expr(value=Name(id='a', ctx=Load()))])"
        self.assertTrue(isinstance(tree, ast.AST))
        self.assertEqual(ast.dump(tree), exp_str)


if __name__ == '__main__':
    unittest.main()

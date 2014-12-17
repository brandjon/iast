"""Unit tests for pynode.py."""


import unittest
import ast

from simplestruct import Struct

from iast.pynode import *


class NodeCase(unittest.TestCase):
    
    def test_node_from_pynode(self):
        node = Name('a', Load())
        self.assertEqual(str(node), 'Name(id=a, ctx=Load())')
        
        self.assertEqual(Name.__bases__, (expr,))
    
    def test_import(self):
        tree = ast.parse('a')
        tree = pyToStruct(tree)
        exp_str = "Module(body=(Expr(value=Name(id='a', ctx=Load())),))"
        self.assertTrue(isinstance(tree, Struct))
        self.assertEqual(str(tree), exp_str)
    
    def test_export(self):
        tree = ast.parse('a')
        exp_str = ast.dump(tree)
        tree = pyToStruct(tree)
        tree = structToPy(tree)
        self.assertTrue(isinstance(tree, ast.AST))
        self.assertEqual(ast.dump(tree), exp_str)
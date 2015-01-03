"""Unit tests for pynode.py."""


import unittest
import ast
import pickle

from iast.node import AST
from iast.python.default import *


class NodeCase(unittest.TestCase):
    
    # The nodes used in these tests are compatible with both
    # Python 3.3 and Python 3.4.
    
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
        tree = eval(self.tree_str, py_nodes)
        tree = structToPy(tree)
        exp_str = "Module(body=[Expr(value=Name(id='a', ctx=Load()))])"
        self.assertTrue(isinstance(tree, ast.AST))
        self.assertEqual(ast.dump(tree), exp_str)
    
    def test_pickle(self):
        # With the craziness of multiple node kinds and import/export
        # trickery, make sure pickling still works.
        node1 = Name('foo', Load())
        s = pickle.dumps(node1)
        node2 = pickle.loads(s)
        self.assertEqual(node1, node2)


if __name__ == '__main__':
    unittest.main()

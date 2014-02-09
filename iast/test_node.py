"""Unit tests for node.py."""


import unittest
import ast

from simplestruct import Struct
from simplestruct.util import trim

from iast.node import *


class NodeCase(unittest.TestCase):
    
    def testNode(self):
        node = Name('a', Load())
        self.assertEqual(str(node), 'Name(id=a, ctx=Load())')
    
    def testImport(self):
        tree = ast.parse('a')
        tree = pyToStruct(tree)
        exp_str = "Module(body=(Expr(value=Name(id='a', ctx=Load())),))"
        self.assertTrue(isinstance(tree, Struct))
        self.assertEqual(str(tree), exp_str)
    
    def testExport(self):
        tree = ast.parse('a')
        exp_str = ast.dump(tree)
        tree = pyToStruct(tree)
        tree = structToPy(tree)
        self.assertTrue(isinstance(tree, ast.AST))
        self.assertEqual(ast.dump(tree), exp_str)
    
    def testDump(self):
        tree = ast.parse('a += b')
        tree = pyToStruct(tree)
        text = dump(tree)
        exp_text = trim('''
            Module(body = [AugAssign(target = Name(id = 'a',
                                                   ctx = Store()),
                                     op = Add(),
                                     value = Name(id = 'b',
                                                  ctx = Load()))])
            ''')
        self.assertEqual(text, exp_text)


if __name__ == '__main__':
    unittest.main()

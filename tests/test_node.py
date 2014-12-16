"""Unit tests for node.py."""


import unittest
import ast

from simplestruct import Struct, Field

from iast.util import trim
from iast.node import *


class NodeCase(unittest.TestCase):
    
    def testNode(self):
        class Foo(AST):
            _fields = ('a', 'b', 'c')
            b = Field()
        node = Foo(1, 2, 3)
        self.assertEqual(str(node), 'Foo(a=1, b=2, c=3)')
    
    def testNodeFromPyNode(self):
        node = Name('a', Load())
        self.assertEqual(str(node), 'Name(id=a, ctx=Load())')
        
        self.assertEqual(Name.__bases__, (expr,))
    
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
        tree = parse('a, b = c')
        text = dump(tree)
        exp_text = trim('''
            Module(body = [Assign(targets = [Tuple(elts = [Name(id = 'a',
                                                                ctx = Store()),
                                                           Name(id = 'b',
                                                                ctx = Store())],
                                                   ctx = Store())],
                                  value = Name(id = 'c',
                                               ctx = Load()))])
            ''')
        self.assertEqual(text, exp_text)


if __name__ == '__main__':
    unittest.main()

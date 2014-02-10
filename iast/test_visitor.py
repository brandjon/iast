"""Unit tests for visitor.py."""


import unittest

from simplestruct.util import trim

from iast.node import parse, dump

from iast.visitor import *


class VisitorCase(unittest.TestCase):
    
    def testVisitor(self):
        class Foo(NodeVisitor):
            def process(self, tree):
                self.names = set()
                super().process(tree)
                return self.names
            def visit_Name(self, node):
                self.names.add(node.id)
        
        tree = parse('a = foo(a)')
        result = Foo.run(tree)
        self.assertEqual(result, {'a', 'foo'})
    
    def testTransformer(self):
        class Foo(NodeTransformer):
            def visit_Name(self, node):
                if node.id == 'a':
                    return node._replace(id='c')
            def visit_Expr(self, node):
                return [node, node]
            def visit_Pass(self, node):
                return []
        
        tree = parse(trim('''
            a
            pass
            '''))
        tree = Foo.run(tree)
        exp_text = trim('''
                Module(body = [Expr(value = Name(id = 'a',
                                                 ctx = Load())),
                               Expr(value = Name(id = 'a',
                                                 ctx = Load()))])
            ''')
        self.assertEqual(dump(tree), exp_text)


if __name__ == '__main__':
    unittest.main()

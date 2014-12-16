"""Unit tests for visitor.py."""


import unittest

from iast.util import trim
from iast.node import parse, dump
from iast.visitor import *


class VisitorCase(unittest.TestCase):
    
    def test_visitor(self):
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
    
    def test_transformer(self):
        # Basic functionality.
        
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
        
        # Make sure None returns aren't propagated to caller.
        
        class Foo(NodeTransformer):
            pass
        
        tree1 = parse('pass')
        tree2 = Foo.run(tree1)
        self.assertEqual(tree1, tree2)
        tree1 = (parse('pass'), parse('pass'))
        tree2 = Foo.run(tree1)
        self.assertEqual(tree1, tree2)
    
    def test_counter(self):
        class Foo(ChangeCounter, NodeTransformer):
            def visit_Name(self, node):
                return node._replace(id=node.id * 2)
        
        instr = {}
        tree = parse('a + b + c + "s"')
        tree = Foo.run(tree, instr)
        exp_tree = parse('aa + bb + cc + "s"')
        
        self.assertEqual(tree, exp_tree)
        self.assertEqual(instr['visited'], 14)
        self.assertEqual(instr['changed'], 9)


if __name__ == '__main__':
    unittest.main()

"""Unit tests for visitor.py."""


import unittest

from iast.util import trim
from iast.node import dump
import iast.python.default as L
from iast.python.default import parse
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
    
    def test_visitor_context(self):
        class Foo(AdvNodeVisitor):
            def process(self, tree):
                self.occ = []
                super().process(tree)
                return self.occ
            def visit_Pass(self, node):
                self.occ.append(self._visit_stack[-1])
            def visit_Name(self, node):
                self.occ.append(self._visit_stack[-1])
        
        tree = parse('''
            pass
            a = b
            ''')
        res = Foo.run(tree)
        exp_res = [
            (L.Pass(), 'body', 0),
            (L.Name('a', L.Store()), 'targets', 0),
            (L.Name('b', L.Load()), 'value', None)
        ]
        self.assertEqual(res, exp_res)
    
    def test_transformer(self):
        # Basic functionality.
        
        class Foo(NodeTransformer):
            def visit_Name(self, node):
                if node.id == 'a':
                    return node._replace(id='c')
            def visit_Expr(self, node):
                node = self.generic_visit(node)
                return [node, node]
            def visit_Pass(self, node):
                return []
        
        tree = parse(trim('''
            a
            pass
            '''))
        tree = Foo.run(tree)
        exp_text = trim('''
                Module(body = (Expr(value = Name(id = 'c',
                                                 ctx = Load())),
                               Expr(value = Name(id = 'c',
                                                 ctx = Load()))))
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
        
        # Unless we want them to be.
        
        class Foo(NodeTransformer):
            _nochange_none = False
            def visit_Num(self, node):
                return None
        
        tree = parse('return 5')
        tree = Foo.run(tree)
        exp_tree = parse('return')
        self.assertEqual(tree, exp_tree)
    
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

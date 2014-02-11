"""Unit tests for pylang.py."""


import unittest

from iast.node import parse, Name, Load, Expr, Module, Tuple, Pass, Num

from iast.pylang import *


class PylangCase(unittest.TestCase):
    
    def testExtract(self):
        tree_in = parse('x')
        
        tree_out = extract_mod(tree_in, mode='mod')
        self.assertEqual(tree_out, tree_in)
        
        tree_out = extract_mod(tree_in, mode='code')
        exp_tree_out = (Expr(Name('x', Load())),)
        self.assertEqual(tree_out, exp_tree_out)
        
        tree_out = extract_mod(Module([]), mode='stmt_or_blank')
        self.assertEqual(tree_out, None)
        tree_out = extract_mod(tree_in, mode='stmt_or_blank')
        self.assertEqual(tree_out, Expr(Name('x', Load())))
        with self.assertRaises(ValueError):
            extract_mod(parse('x; y'), mode='stmt_or_blank')
        
        tree_out = extract_mod(tree_in, mode='stmt')
        self.assertEqual(tree_out, Expr(Name('x', Load())))
        with self.assertRaises(ValueError):
            extract_mod(Module([]), mode='stmt')
        with self.assertRaises(ValueError):
            extract_mod(parse('x; y'), mode='stmt')
        
        tree_out = extract_mod(tree_in, mode='expr')
        exp_tree_out = Name('x', Load())
        self.assertEqual(tree_out, exp_tree_out)
        with self.assertRaises(ValueError):
            extract_mod(parse('pass'), mode='expr')
    
    def testNameExp(self):
        tree = parse('a = b + c')
        subst = {'b': Name('c', Load()), 'c': Name('d', Load())}
        tree = NameExpander.run(tree, subst)
        exp_tree = parse('a = c + d')
        self.assertEqual(tree, exp_tree)
    
    def testMacro(self):
        class Foo(MacroProcessor):
            def handle_ms_foo(self, f, args):
                if len(args) > 1:
                    return Tuple(args, Load())
            def handle_fe_bar(self, f, args):
                return Num(5)
        
        tree = parse('o.foo(bar(1))')
        tree = Foo.run(tree)
        exp_tree = parse('(o, 5)')
        self.assertEqual(tree, exp_tree)


if __name__ == '__main__':
    unittest.main()

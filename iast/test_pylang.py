"""Unit tests for pylang.py."""


import unittest

from simplestruct.util import trim

from iast.node import (parse, Name, Load, Expr, Module,
                       Tuple, Pass, Num, Str, Store)

from iast.pylang import *


class PylangCase(unittest.TestCase):
    
    def testCtx(self):
        tree = extract_mod(parse('(x, [y, z], *(q, r.f))'), mode='expr')
        tree = ContextSetter.run(tree, Store)
        exp_tree = parse('(x, [y, z], *(q, r.f)) = None')
        exp_tree = extract_mod(exp_tree, mode='stmt').targets[0]
        self.assertEqual(tree, exp_tree)
    
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
        
        tree_out = extract_mod(tree_in, mode='lval')
        exp_tree_out = Name('x', Store())
        self.assertEqual(tree_out, exp_tree_out)
    
    def testNameExp(self):
        tree = parse('a = b + c')
        subst = {'b': Name('c', Load()), 'c': Name('d', Load())}
        tree = NameExpander.run(tree, subst)
        exp_tree = parse('a = c + d')
        self.assertEqual(tree, exp_tree)
        
        tree = parse('a.foo.foo')
        subst = {'@foo': 'bar'}
        tree = NameExpander.run(tree, subst)
        exp_tree = parse('a.bar.bar')
        self.assertEqual(tree, exp_tree)
    
    def testMacro(self):
        class Foo(MacroProcessor):
            def handle_ms_foo(self, f, rec, arg):
                return Expr(Tuple((rec, arg), Load()))
            def handle_fe_bar(self, f, arg):
                return Num(5)
        
        tree = parse('o.foo(bar(1))')
        tree = Foo.run(tree)
        exp_tree = parse('(o, 5)')
        self.assertEqual(tree, exp_tree)
    
    def testPyMacro(self):
        # Basic.
        tree = parse('BinOp(4, Add(), 5)')
        tree = PyMacroProcessor.run(tree)
        exp_tree = parse('4 + 5')
        self.assertEqual(tree, exp_tree)
        
        # Statements.
        tree = extract_mod(parse(
                'If(True, Seq(Expr(print(1))), Seq(Pass()))'), 'expr')
        tree = PyMacroProcessor.run(tree)
        exp_tree = extract_mod(parse(trim('''
            if True:
                print(1)
            else:
                pass
            ''')), 'stmt')
        self.assertEqual(tree, exp_tree)
    
    def testASTArgs(self):
        @astargs
        def foo(a, b:'Str'):
            return a + b
        res = foo('x', Str('y'))
        self.assertEqual(res, 'xy')
        
        with self.assertRaises(TypeError):
            foo('x', 'y')
        
        @astargs
        def foo(a:'ids'):
            return ', '.join(a)
        res = foo(extract_mod(parse('[a, b, c]'), 'expr'))
        self.assertEqual(res, 'a, b, c')


if __name__ == '__main__':
    unittest.main()

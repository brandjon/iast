"""Unit tests for pylang.py."""


import unittest

from iast.util import trim
from iast.node import (parse, Name, Load, Expr, Module,
                       Tuple, Pass, Num, Str, Store, BinOp)
from iast.pattern import PatVar, instantiate_wildcards
from iast.pylang import *


class PylangCase(unittest.TestCase):
    
    def pc(self, source):
        return extract_mod(parse(source), 'code')
    
    def ps(self, source):
        return extract_mod(parse(source), 'stmt')
    
    def pe(self, source):
        return extract_mod(parse(source), 'expr')
    
    def test_ctx(self):
        tree = self.pe('(x, [y, z], *(q, r.f))')
        tree = ContextSetter.run(tree, Store)
        exp_tree = self.ps('(x, [y, z], *(q, r.f)) = None').targets[0]
        self.assertEqual(tree, exp_tree)
    
    def test_extract(self):
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
    
    def test_templater(self):
        tree = parse('a = b + c + d')
        subst = {'a': 'a2', 'b': Name('b2', Load()),
                 'c': 'c2', 'd': lambda s: s + '2'}
        tree = Templater.run(tree, subst)
        exp_tree = parse('a2 = b2 + c2 + d2')
        self.assertEqual(tree, exp_tree)
        
        tree = parse('a.foo.foo')
        subst = {'@foo': 'bar'}
        tree = Templater.run(tree, subst)
        exp_tree = parse('a.bar.bar')
        self.assertEqual(tree, exp_tree)
        
        tree = parse('def foo(x): return foo(x)')
        subst = {'<def>foo': 'bar'}
        tree = Templater.run(tree, subst)
        exp_tree = parse('def bar(x): return foo(x)')
        self.assertEqual(tree, exp_tree)
        
        tree = parse('Foo')
        subst = {'<c>Foo': self.pc('pass')}
        tree = Templater.run(tree, subst)
        exp_tree = parse('pass')
        self.assertEqual(tree, exp_tree)
    
    def test_liteval(self):
        # Basic.
        tree = self.pe('(1 + 2) * 5')
        val = literal_eval(tree)
        self.assertEqual(val, 15)
        
        # Comparators, names.
        tree = self.pe('1 < 2 == -~1 and True and None is None')
        val = literal_eval(tree)
        self.assertEqual(val, True)
        
        # Collections.
        tree = self.pe('[1, 2], {3, 4}, {5: "a", 6: "b"}')
        val = literal_eval(tree)
        exp_val = [1, 2], {3, 4}, {5: 'a', 6: 'b'}
        self.assertEqual(val, exp_val)
    
    def test_macro(self):
        class Foo(MacroProcessor):
            def handle_ms_foo(self, f, rec, arg):
                return Expr(Tuple((rec, arg), Load()))
            def handle_fe_bar(self, f, arg):
                return Num(5)
        
        tree = parse('o.foo(bar(1))')
        tree = Foo.run(tree)
        exp_tree = parse('(o, 5)')
        self.assertEqual(tree, exp_tree)
        
        class Foo(MacroProcessor):
            def handle_fw_baz(self, f, arg, _body):
                return (Pass(),) + _body
        
        tree = parse('''
            with baz(1):
                print(5)
            ''')
        tree = Foo.run(tree)
        exp_tree = parse('''
            pass
            print(5)
            ''')
        self.assertEqual(tree, exp_tree)
    
    def test_pymacro(self):
        # Basic.
        tree = parse('BinOp(4, Add(), right=5)')
        tree = PyMacroProcessor.run(tree)
        exp_tree = parse('4 + 5')
        self.assertEqual(tree, exp_tree)
        
        # Statements.
        tree = self.pe('If(True, Seq(Expr(print(1))), Seq(Pass()))')
        tree = PyMacroProcessor.run(tree)
        exp_tree = self.ps('''
            if True:
                print(1)
            else:
                pass
            ''')
        self.assertEqual(tree, exp_tree)
        
        # Omitted arguments.
        tree = self.pe('BinOp(4, right=5)')
        tree = PyMacroProcessor.run(tree, patterns=True)
        exp_tree = BinOp(Num(4), PatVar('_'), Num(5))
        exp_tree = instantiate_wildcards(exp_tree)
        self.assertEqual(tree, exp_tree)
    
    def test_ast_args(self):
        @astargs
        def foo(a, b:'Str'):
            return a + b
        res = foo('x', Str('y'))
        self.assertEqual(res, 'xy')
        
        with self.assertRaises(TypeError):
            foo('x', 'y')
        
        @astargs
        def foo(a:'ids', b:'Name'):
            return ', '.join(a) + ' : ' + b
        res = foo(self.pe('[a, b, c]'), self.pe('d'))
        self.assertEqual(res, 'a, b, c : d')
        
        @astargs
        def foo(a:'err'):
            pass
        with self.assertRaises(TypeError):
            foo(1)


if __name__ == '__main__':
    unittest.main()

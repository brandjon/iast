"""Unit tests for pylang.py."""


import unittest

from iast.util import trim
from iast.pynode import (parse, Name, Load, Expr, Module,
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

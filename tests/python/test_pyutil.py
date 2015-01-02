"""Unit tests for pyutil.py."""


import unittest

from iast.pattern import PatVar, Wildcard
from iast.python.default import *


class PyUtilCase(unittest.TestCase):
    
    def pc(self, source):
        return extract_tree(parse(source), 'code')
    
    def ps(self, source):
        return extract_tree(parse(source), 'stmt')
    
    def pe(self, source):
        return extract_tree(parse(source), 'expr')
    
    def test_make_pattern(self):
        tree = parse('''
            a = (_, _x)
            (_x, _) = b
            ''')
        tree = make_pattern(tree)
        exp_tree = Module((Assign((Name('a', Store()),),
                                  Tuple((Wildcard(), PatVar('_x')),
                                        Load())),
                           Assign((Tuple((PatVar('_x'), Wildcard()),
                                         Store()),),
                                  Name('b', Load()))))
        self.assertEqual(tree, exp_tree)
    
    def test_extract(self):
        tree_in = parse('x')
        
        tree_out = extract_tree(tree_in, mode='mod')
        self.assertEqual(tree_out, tree_in)
        
        tree_out = extract_tree(tree_in, mode='code')
        exp_tree_out = (Expr(Name('x', Load())),)
        self.assertEqual(tree_out, exp_tree_out)
        
        tree_out = extract_tree(Module([]), mode='stmt_or_blank')
        self.assertEqual(tree_out, None)
        tree_out = extract_tree(tree_in, mode='stmt_or_blank')
        self.assertEqual(tree_out, Expr(Name('x', Load())))
        with self.assertRaises(ValueError):
            extract_tree(parse('x; y'), mode='stmt_or_blank')
        
        tree_out = extract_tree(tree_in, mode='stmt')
        self.assertEqual(tree_out, Expr(Name('x', Load())))
        with self.assertRaises(ValueError):
            extract_tree(Module([]), mode='stmt')
        with self.assertRaises(ValueError):
            extract_tree(parse('x; y'), mode='stmt')
        
        tree_out = extract_tree(tree_in, mode='expr')
        exp_tree_out = Name('x', Load())
        self.assertEqual(tree_out, exp_tree_out)
        with self.assertRaises(ValueError):
            extract_tree(parse('pass'), mode='expr')
        
        tree_out = extract_tree(tree_in, mode='lval')
        exp_tree_out = Name('x', Store())
        self.assertEqual(tree_out, exp_tree_out)
    
    def test_ctx(self):
        tree = self.pe('(x, [y, z], *(q, r.f))')
        tree = ContextSetter.run(tree, Store)
        exp_tree = self.ps('(x, [y, z], *(q, r.f)) = None').targets[0]
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
    
    def test_templater(self):
        # Name to string or AST.
        tree = parse('a = b + c')
        subst = {'a': 'a2', 'b': Name('b2', Load()),
                 'c': 'c2'}
        tree = Templater.run(tree, subst)
        exp_tree = parse('a2 = b2 + c2')
        self.assertEqual(tree, exp_tree)
        
        # Attribute name change.
        tree = parse('a.foo.foo')
        subst = {'@foo': 'bar'}
        tree = Templater.run(tree, subst)
        exp_tree = parse('a.bar.bar')
        self.assertEqual(tree, exp_tree)
        
        # Function name change.
        tree = parse('def foo(x): return foo(x)')
        subst = {'<def>foo': 'bar'}
        tree = Templater.run(tree, subst)
        exp_tree = parse('def bar(x): return foo(x)')
        self.assertEqual(tree, exp_tree)
        
        # Code substitution.
        tree = parse('''
            Foo
            Bar
            ''')
        subst = {'<c>Foo': self.pc('pass'),
                 'Foo': 'Foo2',
                 'Bar': 'Bar2'}
        tree = Templater.run(tree, subst)
        exp_tree = parse('''
            pass
            Bar2
            ''')
        self.assertEqual(tree, exp_tree)
        
        # Repeat substitution.
        tree = parse('''
            def foo():
                a.b = c
            Bar
            ''')
        tree2 = self.pc('''
            for x in S:
                Baz
            ''')
        tree3 = self.pc('c')
        subst = {'c': 'c2', 'c2': 'c3',
                 '<def>foo': 'foo2', '<def>foo2': 'foo3',
                 '@b': 'b2', '@b2': 'b3',
                 '<c>Bar': Expr(Name('Bar2', Load())),
                 '<c>Bar2': tree2,
                 '<c>Baz': tree3}
        tree = Templater.run(tree, subst, repeat=True)
        exp_tree = parse('''
            def foo3():
                a.b3 = c3
            for x in S:
                c3
            ''')
        self.assertEqual(tree, exp_tree)
        
        # Bailout limit.
        tree = parse('a')
        subst = {'a': 'a'}
        with self.assertRaises(RuntimeError):
            Templater.run(tree, subst, repeat=True)
        
        # Recursion limit error.
        tree = parse('a')
        subst = {'<c>a': Expr(Name('a', Load()))}
        with self.assertRaises(RuntimeError):
            Templater.run(tree, subst, repeat=True)
    
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
    
    def test_macro(self):
        pe = self.pe
        pc = self.pc
        
        # Handlers for methods and functions, statements and expressions.
        class Foo(MacroProcessor):
            def handle_ms_foo(self, f, rec, arg):
                return Expr(Tuple((rec, arg), Load()))
            def handle_fe_bar(self, f, arg):
                return Num(5)
        
        tree = parse('o.foo(bar(1))')
        tree = Foo.run(tree)
        exp_tree = parse('(o, 5)')
        self.assertEqual(tree, exp_tree)
        
        # With handlers.
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
        
        # Precedence of expression handlers over other handlers.
        class Foo(MacroProcessor):
            def handle_fe_foo(self, f):
                return pe('bar1')
            def handle_fs_foo(self, f):
                return pc('bar2')
            def handle_fw_foo(self, f, arg, _body):
                return pc('bar3')
        
        tree = parse('''
            foo() + 1
            foo()
            with foo():
                pass
        ''')
        tree = Foo.run(tree)
        exp_tree = parse('''
            bar1 + 1
            bar1
            with bar1:
                pass
            ''')
        self.assertEqual(tree, exp_tree)


if __name__ == '__main__':
    unittest.main()

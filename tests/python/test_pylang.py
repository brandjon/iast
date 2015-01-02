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


if __name__ == '__main__':
    unittest.main()

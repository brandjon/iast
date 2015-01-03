"""Unit tests for node.py."""


import unittest
from collections import OrderedDict
from simplestruct import Field

from iast.util import trim
from iast.asdl import parse_asdl
from iast.node import *
from iast.node import ASDLImporter


class NodeCase(unittest.TestCase):
    
    def test_node(self):
        # Define, construct, and repr.
        class Foo(AST):
            _fields = ('a', 'b', 'c')
            b = Field()
        node = Foo(1, 2, 3)
        s = repr(node)
        exp_s = 'Foo(a=1, b=2, c=3)'
        self.assertEqual(s, exp_s)
        
        # Reconstruct the tree from repr.
        node2 = eval(s, locals())
        self.assertEqual(node2, node)
    
    def test_dump(self):
        class Add(AST):
            _fields = ['left', 'right']
        class Sum(AST):
            _fields = ['operands']
        tree = Sum((Add(1, 2), Sum((3, 4,)), Sum((5,)), Sum(()),))
        s = dump(tree)
        exp_s = trim('''
            Sum(operands = (Add(left = 1,
                                right = 2),
                            Sum(operands = (3,
                                            4)),
                            Sum(operands = (5,)),
                            Sum(operands = ())))
            ''')
        self.assertEqual(s, exp_s)
        
        # Reconstruct the tree from dump.
        tree2 = eval(s, locals())
        self.assertEqual(tree2, tree)
    
    asdl_spec = trim('''
        module Dummy
        {
            expr = Sum(expr* operands)
                 | Num(num val)
                 | Unit()
            num = (int real, int? imag)
        }
        ''')
    
    def test_asdl_importer(self):
        asdl = parse_asdl(self.asdl_spec)
        info = ASDLImporter().run(asdl)
        
        exp_info = OrderedDict([
            ('expr', ([], 'AST')),
            ('num', ([('real', 'int', ''), ('imag', 'int', '?')], 'AST')),
            ('Sum', ([('operands', 'expr', '*')], 'expr')),
            ('Num', ([('val', 'num', '')], 'expr')),
            ('Unit', ([], 'expr')),
        ])
        self.assertEqual(info.items(), exp_info.items())
    
    def test_from_asdl_untyped(self):
        asdl = parse_asdl(self.asdl_spec)
        lang = nodes_from_asdl(asdl)
        
        self.assertEqual(lang['AST'], AST)
        self.assertEqual(lang['Sum']._fields, ('operands',))
        self.assertEqual(lang['Sum'].__bases__, (lang['expr'],))
        self.assertEqual(lang['num']._fields, ('real', 'imag'))
        self.assertEqual(lang['num'].__bases__, (lang['AST'],))
    
    def test_from_asdl_typed(self):
        asdl = parse_asdl(self.asdl_spec)
        lang = nodes_from_asdl(asdl, typed=True,
                               primitive_types={'int': int})
        
        Numcls = lang['Num']
        numcls = lang['num']
        
        numcls(1, 2)
        numcls(1, None)
        with self.assertRaises(TypeError):
            numcls('a', 2)
        with self.assertRaises(TypeError):
            numcls(1, 'b')
        
        Numcls(numcls(1, 2))
        with self.assertRaises(TypeError):
            Numcls((1, 2))
        
        Sumcls = lang['Sum']
        Unitcls = lang['Unit']
        with self.assertRaises(TypeError):
            Sumcls(Unitcls())


if __name__ == '__main__':
    unittest.main()

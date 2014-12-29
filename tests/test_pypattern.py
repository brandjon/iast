"""Unit tests for pypattern.py."""


import unittest

from iast.pynode import parse
from iast.visitor import NodeTransformer
from iast.pattern import PatVar
from iast.pypattern import *


class PatternCase(unittest.TestCase):
    
    def test_make_pattern(self):
        tree = parse('''
            a = (_, _x)
            ''')
        tree = make_pattern(tree)
        more_body = parse('''
            (_x, _) = b
            ''')
        new_body = tree.body + more_body.body
        tree = tree._replace(body=new_body)
        tree = make_pattern(tree)
        
        exp_tree = parse('''
            a = (__0, _x)
            (_x, __1) = b
            ''')
        class Trans(NodeTransformer):
            def visit_Name(self, node):
                if node.id.startswith('_'):
                    return PatVar(node.id)
        exp_tree = Trans.run(exp_tree)
        
        self.assertEqual(tree, exp_tree)


if __name__ == '__main__':
    unittest.main()

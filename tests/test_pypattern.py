"""Unit tests for pypattern.py."""


import unittest

from iast.pynode import *
from iast.pattern import PatVar, Wildcard
from iast.pypattern import *


class PatternCase(unittest.TestCase):
    
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


if __name__ == '__main__':
    unittest.main()

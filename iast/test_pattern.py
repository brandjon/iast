"""Unit tests for pattern.py."""


import unittest

from iast.node import parse, Num

from iast.pattern import *


def pat(source):
    return PatMaker.run(parse(source))


class PatternCase(unittest.TestCase):
    
    def testUnify(self):
        # Basic functionality.
        eqs = [
            (pat('_X + _Y'),   pat('1 + _Z')),
            (pat('_Z'),        pat('2')),
        ]
        mapping = unify_eqs(eqs)
        exp_mapping = {
            '_X': Num(1),
            '_Y': Num(2),
            '_Z': Num(2),
        }
        self.assertEqual(mapping, exp_mapping)
        
        # Redundant equation.
        eqs = [
            (pat('_X'),        pat('_X')),
        ]
        mapping = unify_eqs(eqs)
        self.assertEqual(mapping, {})
        
        # Circular equation.
        eqs = [
            (pat('_X'),        pat('_X + 1')),
        ]
        with self.assertRaises(MatchFailure):
            unify_eqs(eqs)


if __name__ == '__main__':
    unittest.main()

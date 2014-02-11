"""Unit tests for pattern.py."""


import unittest

from iast.node import parse, Num, BinOp, Add

from iast.pattern import *


def pat(source):
    return PatMaker.run(parse(source))


class PatternCase(unittest.TestCase):
    
    def testMatch(self):
        # Simple.
        eqs = match_eqs(PatVar('_X'), Num(1))
        exp_eqs = [(PatVar('_X'), Num(1))]
        self.assertEqual(eqs, exp_eqs)
        
        # Var on RHS.
        eqs = match_eqs(Num(1), PatVar('_X'))
        exp_eqs = [(PatVar('_X'), Num(1))]
        self.assertEqual(eqs, exp_eqs)
        
        # Redundant equation.
        eqs = match_eqs(PatVar('_X'), PatVar('_X'))
        self.assertEqual(eqs, [])
        
        # Circular equation.
        with self.assertRaises(MatchFailure):
            match_eqs(PatVar('_X'), BinOp(PatVar('_X'), Add(), Num(1)))
        
        # Nodes, constants.
        eqs = match_eqs(Num(1), Num(1))
        self.assertEqual(eqs, [(1, 1)])
        with self.assertRaises(MatchFailure):
            match_eqs(Num(1), BinOp(Num(1), Add(), Num(2)))
        with self.assertRaises(MatchFailure):
            match_eqs(1, 2)
        
        # Tuples.
        eqs = match_eqs((1, 2), (1, 2))
        exp_eqs = [(1, 1), (2, 2)]
        self.assertEqual(eqs, exp_eqs)
        with self.assertRaises(MatchFailure):
            match_eqs((1, 2), (1, 2, 3))
        
        # Get bindings separately.
        eqs, bindings = match(PatVar('_X'), Num(1))
        self.assertEqual(eqs, [])
        self.assertEqual(bindings, {'_X': Num(1)})
    
    def testUnify(self):
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


if __name__ == '__main__':
    unittest.main()

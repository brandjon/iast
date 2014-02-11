"""Unit tests for pattern.py."""


import unittest

from iast.node import parse, Num, BinOp, Add

from iast.pattern import *
from iast.pattern import match_step


class PatternCase(unittest.TestCase):
    
    def setUp(self):
        self.patmaker = PatMaker()
    
    def pat(self, source):
        return self.patmaker.process(parse(source))
    
    def testMatchStep(self):
        # Simple.
        result = match_step(PatVar('_X'), Num(1))
        exp_result = ([], {'_X': Num(1)})
        self.assertEqual(result, exp_result)
        
        # Var on RHS.
        result = match_step(Num(1), PatVar('_X'))
        exp_result = ([], {'_X': Num(1)})
        self.assertEqual(result, exp_result)
        
        # Redundant equation.
        result = match_step(PatVar('_X'), PatVar('_X'))
        exp_result = ([], {})
        self.assertEqual(result, exp_result)
        
        # Circular equation.
        with self.assertRaises(MatchFailure):
            match_step(PatVar('_X'), BinOp(PatVar('_X'), Add(), Num(1)))
        
        # Nodes, constants.
        result = match_step(Num(1), Num(1))
        exp_result = ([(1, 1)], {})
        self.assertEqual(result, exp_result)
        with self.assertRaises(MatchFailure):
            match_step(Num(1), BinOp(Num(1), Add(), Num(2)))
        with self.assertRaises(MatchFailure):
            match_step(1, 2)
        
        # Tuples.
        result = match_step((1, 2), (1, 2))
        exp_result = ([(1, 1), (2, 2)], {})
        self.assertEqual(result, exp_result)
        with self.assertRaises(MatchFailure):
            match_step((1, 2), (1, 2, 3))
    
    def testMatch(self):
        result = match(self.pat('((_X, _Y), _Z + _)'),
                       self.pat('((1, _Z), 2 + 3)'))
        exp_result = {
            '_X': Num(1),
            '_Y': Num(2),
            '_Z': Num(2),
        }
        self.assertEqual(result, exp_result)
        
        result = match(1, 2)
        self.assertEqual(result, None)


if __name__ == '__main__':
    unittest.main()

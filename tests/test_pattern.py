"""Unit tests for pattern.py."""


import unittest

from iast.python.default import parse, make_pattern, Num, BinOp, Add, Mult
from iast.pattern import *
from iast.pattern import match_step


class PatternCase(unittest.TestCase):
    
    def pat(self, source):
        return make_pattern(parse(source))
    
    def pe(self, source):
        return parse(source).body[0].value
    
    def pate(self, source):
        return self.pat(source).body[0].value
    
    def test_match_step(self):
        # Simple.
        result = match_step(PatVar('_X'), Num(1))
        exp_result = ([], {'_X': Num(1)})
        self.assertEqual(result, exp_result)
        
        # Wildcard.
        result = match_step(Wildcard(), Num(1))
        exp_result = ([], {})
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
    
    def test_match(self):
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
    
    def test_pattrans(self):
        class Trans(PatternTransformer):
            rules = [
                # Constant-fold addition.
                (BinOp(Num(PatVar('_X')), Add(), Num(PatVar('_Y'))),
                    lambda _X, _Y: Num(_X + _Y)),
                # Constant-fold left-multiplication by 0,
                # defer to other rules.
                (BinOp(Num(PatVar('_X')), Mult(), Num(PatVar('_Y'))),
                    lambda _X, _Y: Num(0) if _X == 0 else NotImplemented),
                # Constant-fold right-multiplication by 0,
                # do not defer to other rules.
                (BinOp(Num(PatVar('_X')), Mult(), Num(PatVar('_Y'))),
                    lambda _X, _Y: Num(0) if _Y == 0 else None),
                # Constant-fold multiplication, but never gets
                # to run since above rule doesn't defer.
                (BinOp(Num(PatVar('_X')), Mult(), Num(PatVar('_Y'))),
                    lambda _X, _Y: Num(_X * _Y)),
            ]
        
        # Bottom-up; subtrees should be processed first.
        tree = parse('1 + (2 + 3)')
        tree = Trans.run(tree)
        exp_tree = parse('6')
        self.assertEqual(tree, exp_tree)
        
        # NotImplemented defers to third rule, None blocks last rule.
        tree = parse('(5 * 2) * ((3 * 0) - 1)')
        tree = Trans.run(tree)
        exp_tree = parse('(5 * 2) * (0 - 1)')
        self.assertEqual(tree, exp_tree)


if __name__ == '__main__':
    unittest.main()

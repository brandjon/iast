"""Unit tests for pyutil.py."""


import unittest

from iast.python.default import *


class PyUtilCase(unittest.TestCase):
    
    def ps(self, source):
        return extract_tree(parse(source), 'stmt')
    
    def pe(self, source):
        return extract_tree(parse(source), 'expr')
    
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


if __name__ == '__main__':
    unittest.main()

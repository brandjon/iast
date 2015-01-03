import unittest

def additional_tests():
    return unittest.defaultTestLoader.discover(
                'iast.asdl', pattern='*_test.py')

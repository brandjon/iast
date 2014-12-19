"""This subpackage is derived from Eli Bendersky's rewrite of the
Python ASDL parser, which has been incorporated into CPython.
asdl.py and asdl_test.py are directly from

    https://github.com/eliben/asdl_parser

with minor modification to work in this subpackage. Python33.asdl and
Python34.asdl are from their respective versions of the CPython source
distribution (Parser/Python.asdl).

See also:

    http://bugs.python.org/issue19655
"""


__all__ = [
    'primitive_types',
    'python33_asdl',
    'python34_asdl',
    # ...
]


from os.path import join, dirname

from .asdl import *
from .asdl import __all__ as _asdl_all, parse as _asdl_parse
__all__.extend(_asdl_all)

primitive_types = {
    'identifier': str,
    'int': int,
    'string': str,
    'bytes': bytes,
    'object': object,
    'singleton': object,
}

# Redefine parse() to accept a string rather than an open file.

def parse(asdl_source):
    from .asdl import ASDLParser
    parser = ASDLParser()
    return parser.parse(asdl_source)

py_asdl33_filename = join(dirname(__file__), 'Python33.asdl')
py_asdl34_filename = join(dirname(__file__), 'Python34.asdl')
python33_asdl = _asdl_parse(py_asdl33_filename)
python34_asdl = _asdl_parse(py_asdl34_filename)

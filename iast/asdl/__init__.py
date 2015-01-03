"""This subpackage is derived from Eli Bendersky's rewrite of the
Python ASDL parser, which has been incorporated into CPython.
asdl.py and asdl_test.py are directly from

    https://github.com/eliben/asdl_parser

with minor modification to work as a subpackage. They are
covered by the PSF license. See also:

    http://bugs.python.org/issue19655

Python33.asdl and Python34.asdl are from their respective versions
of the CPython source distribution (Parser/Python.asdl). They are
covered by the PSF license.
"""


__all__ = [
    'parse_asdl',
    'primitive_types',
    'python33_asdl',
    'python34_asdl',
    # ...
]


from os.path import join, dirname

from .asdl import ASDLParser


primitive_types = {
    'identifier': str,
    'int': int,
    'string': str,
    'bytes': bytes,
    'object': object,
    'singleton': object,
}

def parse_asdl(asdl_source):
    parser = ASDLParser()
    return parser.parse(asdl_source)

py_asdl33_filename = join(dirname(__file__), 'Python33.asdl')
py_asdl34_filename = join(dirname(__file__), 'Python34.asdl')
with open(py_asdl33_filename, 'rt') as file:
    python33_asdl = parse_asdl(file.read())
with open(py_asdl34_filename, 'rt') as file:
    python34_asdl = parse_asdl(file.read())

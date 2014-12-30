"""Subpackage for Python-specific AST definitions and utilities.

Python33.asdl and Python34.asdl are from their respective versions
of the CPython source distribution (Parser/Python.asdl). They are
covered by the PSF license.
"""

from os.path import join, dirname

from ..asdl import _asdl_parse

py_asdl33_filename = join(dirname(__file__), 'Python33.asdl')
py_asdl34_filename = join(dirname(__file__), 'Python34.asdl')
python33_asdl = _asdl_parse(py_asdl33_filename)
python34_asdl = _asdl_parse(py_asdl34_filename)

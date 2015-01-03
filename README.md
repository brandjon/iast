# iAST #

*(Supports Python 3.3 and 3.4)*

This library provides a way of defining and transforming abstract syntax
trees (ASTs) for custom languages. It can be used to help build a compiler
or other program transformation system.

iAST reads your language's abstract syntax from an ASDL grammar, and
automatically generates node classes. A standard visitor-style framework
is provided for traversing, transforming, and pattern matching over trees.
Nodes are hashable, have structural equality, and support optional type
checking. (Parsing is not supported and should be handled by an external
parser generator.)

Node definitions for the ASTs of Python 3.3 and Python 3.4 are provided
out-of-the-box, along with tools for writing code templates and macros
targeting Python code. However, the main framework works on ASTs for
arbitrary languages.

## Examples ##

See [arith.py](examples/arith.py) for basic usage and visitors/transformers.
See [toy.py](examples/toy.py) for a comparison with Python's own ast module
and the use of type checking. Both examples use abstract grammars from the
corresponding ASDL files.

## Installation ##

To install from pip/PyPI:

```
python -m pip install iast
```

To use a development version:

```
python -m pip install https://github.com/brandjon/iast/tree/tarball/develop
```

Python 3.3 and 3.4 are supported. The only dependency is
[simplestruct](https://github.com/brandjon/simplestruct), which is used to
define the node classes.

## Developers ##

Tests can be run with `python setup.py test`, or by installing
[Tox](http://testrun.org/tox/latest/) and running `python -m tox`
in the project root. Tox tests both Python 3.3 and 3.4 configurations.
Building a source distribution (`python setup.py sdist`) requires the
setuptools extension package
[setuptools-git](https://github.com/wichert/setuptools-git).

## References ##

[1]: https://github.com/eliben/asdl_parser
[[1]]: Eli Bendersky's rewrite of the Python ASDL parser, which powers
iAST's generation of nodes from ASDL.

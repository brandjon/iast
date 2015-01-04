from setuptools import setup

setup(
    name =          'iAST',
    version =       '0.2.1',
    url =           'https://github.com/brandjon/iast',
    
    author =        'Jon Brandvein',
    author_email =  'jon.brandvein@gmail.com',
    license =       'MIT License',
    description =   'A library for defining and manipulating ASTs',
    
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    
    packages =      ['iast', 'iast.asdl', 'iast.python'],
    package_data =  {'iast.asdl': ['*.asdl']},
    
    test_suite =    'tests',
    
    install_requires = ['simplestruct >=0.2.1'],
)

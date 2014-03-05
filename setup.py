"""Setup for gu.z3cform.rdf
"""
import os
from setuptools import setup, find_packages

version = '0.6-dev'


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


def _modname(path, base, name=''):
    if path == base:
        return name
    dirname, basename = os.path.split(path)
    return _modname(dirname, base, basename + '.' + name)


def alltests():
    import logging
    import pkg_resources
    import unittest

    class NullHandler(logging.Handler):
        level = 50

        def emit(self, record):
            pass

    logging.getLogger().addHandler(NullHandler())

    suite = unittest.TestSuite()
    base = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('zope.schema')).location
    for dirpath, dirnames, filenames in os.walk(base):
        if os.path.basename(dirpath) == 'tests':
            for filename in filenames:
                if filename.endswith('.py') and filename.startswith('test'):
                    mod = __import__(
                        _modname(dirpath, base, os.path.splitext(filename)[0]),
                        {}, {}, ['*'])
                    suite.addTest(mod.test_suite())
        elif 'tests.py' in filenames:
            continue
            mod = __import__(_modname(dirpath, base, 'tests'), {}, {}, ['*'])
            suite.addTest(mod.test_suite())
    return suite

REQUIRES = [
        'setuptools',
        'zope.schema',
        'zope.component',
        'zope.interface',
        'zope.dottedname', # TODO: keep until fieldfactory lookup becomes adapter lookup
        'z3c.form',
        'rdflib',
        'z3c.formwidget.query',
        'plone.z3cform',
        'plone.supermodel', # TODO: optional?
        'ordf',
        ]

TESTS_REQUIRE = [
    #'zope.testing',
    'z3c.form [test]',
    ]

setup(name='gu.z3cform.rdf',
      version=version,
      url='http://pypi.python.org/pypi/zope.schema',
      license='ZPL 2.1',
      description='zope.interface extension for defining data schemas',
      author='Gerhard Weis',
      author_email='g.weis@griffith.edu.au',
      #long_description=(read('README.txt') + '\n\n' + read('CHANGES.txt')),
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['gu', 'gu.z3cform'],
      install_requires=REQUIRES,
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Zope Public License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      include_package_data=True,
      zip_safe=False,
      # FIXME: set alltests correctly
      test_suite='__main__.alltests',
      tests_require=TESTS_REQUIRE,
      extras_require={
        'docs': ['Sphinx'],
        'test': TESTS_REQUIRE,
        'testing': TESTS_REQUIRE + ['nose2', 'noze2-cov'],
      },
)

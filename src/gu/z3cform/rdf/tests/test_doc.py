import doctest
import unittest
from z3c.form import testing
from z3c.form import outputchecker
from zope.configuration import xmlconfig

def setUp(test):
    import gu.z3cform.rdf
    testing.setUp(test)
    xmlconfig.XMLConfig('configure.zcml', gu.z3cform.rdf)()

def test_suite():
    checker = outputchecker.OutputChecker(doctest)

    tests = ((
        doctest.DocFileSuite(
            '../form.txt',
            setUp=setUp, tearDown=testing.tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
            checker=checker,
            ),
    ))
    return unittest.TestSuite(tests)

def load_tests(loader, tests, pattern):
    return test_suite()

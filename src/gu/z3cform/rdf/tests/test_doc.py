import doctest
import unittest
from z3c.form import testing
from z3c.form import outputchecker
from zope.configuration import xmlconfig
from zope.interface import implementer
from gu.z3cform.rdf.interfaces import IORDF
from zope.component import provideUtility


class MockHandler(object):

    def put(self, graph):
        pass


@implementer(IORDF)
class MockIORDFUtility(object):

    def getHandler(self):
        return MockHandler()


def setUp(test):
    testing.setUp(test)
    # load test setup
    import gu.z3cform.rdf.tests
    xmlconfig.XMLConfig('testing.zcml', gu.z3cform.rdf.tests)()
    # load package configuration
    import gu.z3cform.rdf
    xmlconfig.XMLConfig('configure.zcml', gu.z3cform.rdf)()
    provideUtility(MockIORDFUtility())


def test_suite():
    checker = outputchecker.OutputChecker(doctest)

    tests = ((
        doctest.DocFileSuite(
            '../form.txt',
            setUp=setUp, tearDown=testing.tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=checker,
            ),
    ))
    return unittest.TestSuite(tests)

# def load_tests(loader, tests, pattern):
#     return test_suite()

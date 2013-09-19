import doctest
import unittest
import os.path
from z3c.form import testing
from z3c.form import outputchecker
from z3c.form import form
from z3c.form.interfaces import DISPLAY_MODE
from zope.configuration import xmlconfig
from zope.interface import implementer
from gu.z3cform.rdf.interfaces import IORDF
from gu.z3cform.rdf.fresnel.fresnel import Fresnel
from zope.component import provideUtility, getUtility
from plone.z3cform.fieldsets.extensible import ExtensibleForm
from ordf.graph import Graph, ConjunctiveGraph
from rdflib import RDF, URIRef


class MockHandler(object):

    store = None

    def put(self, graph):
        for s, p, o in graph:
            self.store.add((s, p, o, graph.identifier))

    def get(self, identifier):
        graph = self.store.get_context(identifier)
        return Graph(store=graph.store,
                     identifier=graph.identifier)


@implementer(IORDF)
class MockIORDFUtility(object):

    fresnel = None
    handler = None

    def getHandler(self):
        if self.handler is None:
            self.handler = MockHandler()
        return self.handler

    def getFresnel(self):
        if self.fresnel is None:
            formatgraph = Fresnel()
            formatgraph.parse(os.path.join(os.path.dirname(__file__),
                                           'test_defs.ttl'),
                              format='turtle')
            formatgraph.compile()
            self.fresnel = formatgraph
        return self.fresnel

    def getBaseURI(self):
        return u"http://example.com/"

    def generateURI(self):
        import uuid
        uri = u"{}{}".format(self.getBaseURI(), uuid.uuid1())
        return URIRef(uri)


class ExtensibleAddForm(ExtensibleForm, form.AddForm):

    def create(self, data):
        # create object
        content =  Graph()
        # apply form.rdftype
        content.add((content.identifier, RDF['type'], self.rdftype))
        # apply form data
        # FIXME: we have a problem here. the datamanager already puts it into the
        #        hnadler.
        form.applyChanges(self, content, data)
        for group in self.groups:
            form.applyChanges(group, content, data)
        return content

    def add(self, object):
        # put stuff into store via handler
        # FIXME: has already been added by create. see above
        getUtility(IORDF).getHandler().put(object)

    def nextURL(self):
        # nothing useful to do here
        self.request.getURL()


class ExtensibleEditForm(ExtensibleForm, form.EditForm):

    pass


class ExtensibleDisplayForm(ExtensibleForm, form.Form):

    mode = DISPLAY_MODE


def setUp(test):
    testing.setUp(test)
    # load dependency test setup
    import plone.z3cform
    xmlconfig.XMLConfig('testing.zcml', plone.z3cform)()
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
        doctest.DocFileSuite(
            '../object.txt',
            setUp=setUp, tearDown=testing.tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            checker=checker,
            ),
    ))
    return unittest.TestSuite(tests)

# def load_tests(loader, tests, pattern):
#     return test_suite()

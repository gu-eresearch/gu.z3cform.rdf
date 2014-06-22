import os.path
from ordf.graph import Graph, ConjunctiveGraph
from gu.z3cform.rdf.interfaces import IORDF
from zope.interface import implementer
from rdflib import URIRef
from plone.z3cform.fieldsets.extensible import ExtensibleForm
from z3c.form import form
from z3c.form.interfaces import DISPLAY_MODE
from zope.component import getUtility
from rdflib import RDF


class MockHandler(object):

    store = None

    _cache = None

    def __init__(self):
        self._cache = {}
        self.store = ConjunctiveGraph()

    def put(self, graph):
        # copy given graph into store
        # remove old data
        #self.store.remove_context(graph.identifier)
        # TODO: something weird is going with the above when using
        #       BNodes as graph.identifier code below works as
        #       expected
        self.store.remove((None, None, None, graph.identifier))
        # add new data
        for s, p, o in graph:
            self.store.add((s, p, o, graph.identifier))
        # remove from _cache
        if graph.identifier in self._cache:
            del self._cache[graph.identifier]

    def get(self, identifier):
        # simple check out mechanism.
        # the handler returns the same graph as long as it's not put back
        if identifier in self._cache:
            return self._cache[identifier]
        graph = self.store.get_context(identifier)
        # make a copy of the graph
        cgraph = Graph(identifier=identifier)
        for t in graph:
            cgraph.add(t)
        self._cache[identifier] = cgraph
        return cgraph

    def remove(self, identifier):
        self.store.remove((None, None, None, identifier))
        if identifier in self._cache:
            del self._cache[identifier]

    def query(self, query):
        return self.store.query(query)


@implementer(IORDF)
class MockIORDFUtility(object):

    handler = None

    def getHandler(self):
        if self.handler is None:
            self.handler = MockHandler()
        return self.handler

    def getBaseURI(self):
        return u"http://example.com/"

    def generateURI(self):
        import uuid
        uri = u"{}{}".format(self.getBaseURI(), uuid.uuid1())
        return URIRef(uri)


class ExtensibleAddForm(ExtensibleForm, form.AddForm):

    def create(self, data):
        # create object
        content = Graph()
        # apply form.rdftype
        content.add((content.identifier, RDF['type'], self.rdftype))
        # apply form data
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

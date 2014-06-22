from zope.interface import implements
from gu.z3cform.rdf.interfaces import IIndividual
from ordf.vocab.owl import AnnotatibleTerms
from gu.z3cform.rdf.interfaces import IRDFTypeMapper
from zope.interface import implementer
from rdflib import RDF

def GetIndividual(graph):
    return AnnotatibleTerms(identifier=graph.identifier,
                            graph=graph)

@implementer(IRDFTypeMapper)
class RDFTypeMapper(object):

    def __init__(self, context, request, form):
        self.context = context
        self.request = request
        self.form = form

    def applyTypes(self, graph):
        graph.add((graph.identifier, RDF['type'], self.form.rdftype))

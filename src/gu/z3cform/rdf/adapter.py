from zope.interface import implements
from gu.z3cform.rdf.interfaces import IIndividual
from ordf.vocab.owl import AnnotatibleTerms

def GetIndividual(graph):
    return AnnotatibleTerms(identifier=graph.identifier,
                            graph=graph)

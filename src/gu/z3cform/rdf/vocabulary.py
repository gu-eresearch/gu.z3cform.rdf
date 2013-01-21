from zope.schema.interfaces import IVocabularyFactory
from zope.interface import implements
from zope.component import getUtility
from gu.z3cform.rdf.interfaces import IORDF
from zope.schema.vocabulary import SimpleVocabulary, TreeVocabulary
from z3c.formwidget.query.interfaces import IQuerySource
from rdflib.namespace import split_uri
from collections import defaultdict

class QuerySimpleVocabulary(SimpleVocabulary):

    implements(IQuerySource)

    def search(self, query_string):
        return (term for term in self if query_string in term.value.lower())


class GraphVocabularyFactory(object):

    implements(IVocabularyFactory)

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        g = h.query("select distinct ?g Where { graph ?g { ?s ?p ?o } }")
        # FIXME: do some rdflib-sparql sepacialities here:
        uris = sorted([item[0] for item in g])
        # this here would be the natural way when parsing a sparql-xml-result
        #uris = sorted([item['g'] for item in g])
        return QuerySimpleVocabulary.fromValues(uris)

# FIXME: move this dictionary to IORDf tool to make it configurable,... maybe turn it into an rdf graph?
#        graph to check for ontology labels, namespace prefixes etc..., language aware?
NAMESPACES = {
    'http://xmlns.com/foaf/0.1/': ('foaf', u'FOAF'),
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': ('rdf', u'RDF'),
    'http://www.w3.org/2000/01/rdf-schema#': ('rdfs', u'RDFS'),
    'http://www.w3.org/2002/07/owl': ('owl', u'OWL'),
    }

class SparqlTreeVocabularyFactory(object):
    # group returned URIs by namespace.

    implements(IVocabularyFactory)

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        r = h.query("select distinct ?uri ?title "
                    "Where "
                    "{ ?uri a %s . "
                    "  optional { ?uri <http://www.w3.org/2000/01/rdf-schema#label> ?title . }"
                    "  filter ( !isBlank(?uri) ) "
                    "} "
                    "order by ?title" 
                    % context.n3())
        # this here would be the natural way when parsing a sparql-xml-result
        #uris = sorted([item['g'] for item in g])

        terms = defaultdict(defaultdict)
        for item in r:
            ns, local = split_uri(item[0])
            if ns in NAMESPACES:
                groupkey = (ns, ns, NAMESPACES[ns][1])
            else:
                groupkey = (ns, ns, ns)
            
            valuekey = (item[0], item[0], item[1] or item[0])
            terms[groupkey][valuekey] = {}

        return TreeVocabulary.fromDict(terms)
        

class SparqlVocabularyFactory(object):

    implements(IVocabularyFactory)

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        r = h.query("select distinct ?uri ?title "
                    "Where "
                    "{ ?uri a %s . "
                    "  optional { ?uri <http://www.w3.org/2000/01/rdf-schema#label> ?title . }"
                    "  filter ( !isBlank(?uri) ) "
                    "} "
                    "order by ?title" 
                    % context.n3())
        # this here would be the natural way when parsing a sparql-xml-result
        #uris = sorted([item['g'] for item in g])

        terms = []
        for item in r:
            term = SimpleVocabulary.createTerm(item[0], item[0], item[1] or item[0])
            terms.append(term)
        return QuerySimpleVocabulary(terms)
        

# Property Vocabulary ...
#  ... describe vocabularies in rdf as sparql queries?
#  ->          as 
#  ... ordered by namespace, property label (id)

from string import Template
from zope.schema.interfaces import IVocabularyFactory, ITitledTokenizedTerm
from zope.interface import implements
from zope.component import getUtility
from gu.z3cform.rdf.interfaces import IORDF, ISparqlVocabularyTool
from zope.schema.vocabulary import SimpleVocabulary, TreeVocabulary, SimpleTerm
from z3c.formwidget.query.interfaces import IQuerySource
from rdflib.namespace import split_uri
from collections import defaultdict


class QuerySimpleVocabulary(SimpleVocabulary):

    implements(IQuerySource)

    def cmp(self, term, query):
        # ajax search widget does a search on this vocabulary,
        # if we have titled terms, we have to compare against the title
        # otherwise use the value.
        if ITitledTokenizedTerm.providedBy(term):
            return query in term.title.lower()
        return query in term.value.lower()

    def search(self, query_string):
        query = query_string.lower()
        return (term for term in self if self.cmp(term, query))


class GraphVocabularyFactory(object):

    implements(IVocabularyFactory)

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        g = h.query("select distinct ?g Where { graph ?g { ?s ?p ?o } }")
        # FIXME: do some rdflib-sparql specialities here:
        uris = sorted([item[0] for item in g])
        # this here would be the natural way when parsing a sparql-xml-result
        #uris = sorted([item['g'] for item in g])
        return QuerySimpleVocabulary.fromValues(uris)


# FIXME: move this dictionary to IORDf tool to make it configurable,... (see ord utils for namespace bindings)
#        -> maybe turn it into an rdf graph?
#        graph to check for ontology labels, namespace prefixes etc...,
#        -> language aware?
NAMESPACES = {
    'http://xmlns.com/foaf/0.1/': ('foaf', u'FOAF'),
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': ('rdf', u'RDF'),
    'http://www.w3.org/2000/01/rdf-schema#': ('rdfs', u'RDFS'),
    'http://www.w3.org/2002/07/owl': ('owl', u'OWL'),
}


class SparqlTreeVocabularyFactory(object):
    # group returned URIs by namespace.

    implements(IVocabularyFactory)

    def __init__(self, classuri):
        self.classuri = classuri

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        r = h.query("select distinct ?uri ?title "
                    "Where "
                    "{ Graph?g "
                    "  { ?uri a %s . "
                    "    optional { ?uri <http://www.w3.org/2000/01/rdf-schema#label> ?title . }"
                    "    filter ( !isBlank(?uri) ) "
                    "  }"
                    "} "
                    "order by ?title"
                    % self.classuri.n3())
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


class SparqlInstanceVocabularyFactory(object):

    implements(IVocabularyFactory)

    def __init__(self, classuri, orderby=None):
        self.classuri = classuri
        self.orderby = orderby

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        if self.orderby:
            query = ("select distinct ?uri ?title "
                     "Where "
                     "{ Graph?g "
                     "  { ?uri a %s . "
                     "    optional { ?uri <http://www.w3.org/2000/01/rdf-schema#label> ?title . }"
                     "    optional { ?uri %s ?ordervar . }"
                     "    filter ( !isBlank(?uri) ) "
                     "  }"
                     "} "
                     "order by ?ordervar ?title"
                     % (self.classuri.n3(), self.orderby.n3()))
        else:
            query = ("select distinct ?uri ?title "
                     "Where "
                     "{ Graph?g "
                     "  { ?uri a %s . "
                     "    optional { ?uri <http://www.w3.org/2000/01/rdf-schema#label> ?title . }"
                     "    filter ( !isBlank(?uri) ) "
                     "  }"
                     "} "
                     "order by ?title"
                     % self.classuri.n3())

        r = h.query(query)
        terms = []
        for item in r:
            term = SimpleVocabulary.createTerm(item[0], item[0], item[1] or
                                               item[0])
            terms.append(term)
        return QuerySimpleVocabulary(terms)


class SparqlVocabularyFactory(object):

    implements(IVocabularyFactory)

    def __init__(self, query):
        self.query = Template(query)

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        params = getUtility(ISparqlVocabularyTool).getContextualParameters(context)
        r = h.query(self.query.safe_substitute(params))
        # this here would be the natural way when parsing a sparql-xml-result
        #uris = sorted([item['g'] for item in g])

        # the query should return value, title, token, whereas title and token
        # are optional
        terms = []
        for item in r:
            if len(item) >= 3:
                term = SimpleTerm(value=item[0],
                                  token=item[2],
                                  title=item[1])
            elif len(item) == 2:
                term = SimpleTerm(value=item[0],
                                  title=item[1])
            else:
                term = SimpleTerm(value=item[0])
            terms.append(term)
        return QuerySimpleVocabulary(terms)


# Property Vocabulary ...
#  ... describe vocabularies in rdf as sparql queries?
#  ->          as
#  ... ordered by namespace, property label (id)

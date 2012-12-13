from zope.schema.interfaces import IVocabularyFactory
from zope.interface import implements
from zope.component import getUtility
from gu.z3cform.rdf.interfaces import IORDF
from zope.schema.vocabulary import SimpleVocabulary


class GraphVocabularyFactory(object):

    implements(IVocabularyFactory)

    def __call__(self, context):
        h = getUtility(IORDF).getHandler()
        g = h.query("select distinct ?g Where { graph ?g { ?s ?p ?o } }")
        # FIXME: do some rdflib-sparql sepacialities here:
        uris = sorted([item[0] for item in g])
        # this here would be the natural way when parsing a sparql-xml-result
        #uris = sorted([item['g'] for item in g])
        return SimpleVocabulary.fromValues(uris)



# Property Vocabulary ...
#  ... describe vocabularies in rdf as sparql queries?
#  ->          as 
#  ... ordered by namespace, property label (id)

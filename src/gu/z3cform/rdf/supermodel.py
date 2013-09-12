from plone.supermodel import exportimport
from gu.z3cform.rdf import schema
from rdflib import URIRef


class RDFBaseHandler(exportimport.BaseHandler):

    def __init__(self, klass):
        super(RDFBaseHandler, self).__init__(klass)

    def _constructField(self, attributes):
        # FIXME .... use propery URIRef field in IRDFN3Field interface
        attributes['prop'] = URIRef(attributes['prop'])
        return super(RDFBaseHandler, self)._constructField(attributes)

    def read(self, element):
        # import ipdb; ipdb.set_trace()
        return super(RDFBaseHandler, self).read(element)

# FIXME:
#  add additional special handlers for:
#    rdftype (some felds have fixed/default values here)
#    rdflang
#    SparqTreeVocabulary?
#  and RDFObjectField:
#    classuri
#    sub schema?

RDFN3Handler = RDFBaseHandler(schema.RDFN3Field)
RDFLiteralHandler = RDFBaseHandler(schema.RDFLiteralField)
RDFLiteralLineHandler = RDFBaseHandler(schema.RDFLiteralLineField)
RDFDateHandler = RDFBaseHandler(schema.RDFDateField)
RDFDateRangeHandler = RDFBaseHandler(schema.RDFDateRangeField)
RDFURIRefHandler = RDFBaseHandler(schema.RDFURIRefField)
RDFURIChoiceHandler = RDFBaseHandler(schema.RDFURIChoiceField)
RDFGroupedURIChoiceHandler = RDFBaseHandler(schema.RDFGroupedURIChoiceField)
RDFObjectHandler = RDFBaseHandler(schema.RDFObjectField)

from z3c.form.interfaces import IWidget
from z3c.form.converter import BaseDataConverter
from rdflib.util import from_n3
from gu.z3cform.rdf.interfaces import (IRDFN3Field, IRDFTypeMapper)
from zope.interface import implementer
from zope.component import adapter
from rdflib import RDF


@adapter(IRDFN3Field, IWidget)
class RDFN3DataConverter(BaseDataConverter):
    """
    use rdflibs n3 parser/generator to convert values.

    This converter accepts an n3 formatted object value and converts it into an
    rdflib Node instance.
    """

    def __init__(self, field, widget):
        self.field = field
        self.widget = widget

    def toFieldValue(self, value):
        if value == u'':
            return self.field.missing_value
        return from_n3(value)

    def toWidgetValue(self, value):
        if value is None:
            return None
        return value.n3()


# TODO: move somewhere else
@implementer(IRDFTypeMapper)
class RDFTypeMapper(object):

    def __init__(self, context, request, form):
        self.context = context
        self.request = request
        self.form = form

    def applyTypes(self, graph):
        graph.add((graph.identifier, RDF['type'], self.form.rdftype))

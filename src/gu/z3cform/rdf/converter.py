from zope.component import adapts
from z3c.form.interfaces import IWidget
from z3c.form.converter import BaseDataConverter
from rdflib.util import from_n3
from gu.z3cform.rdf.interfaces import IRDFN3Field


class RDFN3DataConverter(BaseDataConverter):
    """
    use rdflibs n3 parser/generator to convert values.

    This converter accepts an n3 formatted object value and converts it into an
    rdflib Node instance.
    """

    adapts(IRDFN3Field, IWidget)

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

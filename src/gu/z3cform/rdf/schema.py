from zope.interface import implements
from zope.schema import Text
from rdflib import Literal, URIRef
from rdflib.util import from_n3
from gu.z3cform.rdf.interfaces import IRDFN3Field


class RDFN3Field(Text):
    """
    A field that knows how to handle n3 formatted values.

    TODO: implement validation
    """

    _type = (Literal, URIRef)

    prop = None

    implements(IRDFN3Field)

    def __init__(self, prop, **kw):
        super(RDFN3Field, self).__init__(**kw)
        # TODO: should type chek prop here. (how is z3c doing this? with FieldProperty?)
        #       -> also check if __name__ is useful in case of ordf's ORM
        self.prop = prop

    def fromUnicode(self, str):
        value = from_n3(str)
        self.validate(value)
        return value

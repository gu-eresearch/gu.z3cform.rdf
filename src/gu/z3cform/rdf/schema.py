from zope.interface import implements
from zope.schema import Text, List, TextLine, URI
from rdflib import Literal, URIRef
from rdflib.util import from_n3
from gu.z3cform.rdf.interfaces import IRDFN3Field, IRDFMultiValueField
from gu.z3cform.rdf.interfaces import IRDFLiteralField, IRDFLiteralLineField
from gu.z3cform.rdf.interfaces import IRDFURIRefField

# TODO: for specilised fields like URIRef, or Literal field:
#       in case there is data in the graph, that does not match the type
#       leave the data untouched (don't display, and don't change/edit/delete if possible)

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
        #       -> name might also be used as ID combined with default namespace
        self.prop = prop

    def fromUnicode(self, str):
        value = from_n3(str)
        self.validate(value)
        return value


class RDFLiteralField(TextLine):

    implements(IRDFLiteralField)

    _type = Literal

    def __init__(self, prop, rdftype=None, rdflang=None, **kw):
        super(RDFLiteralField, self).__init__(**kw)
        self.prop = prop
        self.rdftype = rdftype
        self.rdflang = rdflang

    def fromUnicode(self, str):
        # TODO: ensure only rdftye or rdflang is given and use these values in fromUnicode
        value = Literal(str)
        self.validate(value)
        return value


class RDFLiteralLineField(Text):

    implements(IRDFLiteralLineField)

    _type = Literal

    def __init__(self, prop, rdftype=None, rdflang=None, **kw):
        super(RDFLiteralLineField, self).__init__(**kw)
        # TODO: ensure only rdftye or rdflang is given and use these values in fromUnicode
        self.prop = prop
        self.rdftype = rdftype
        self.rdflang = rdflang

    def fromUnicode(self, str):
        value = Literal(str)
        self.validate(value)
        return value
    


class RDFURIRefField(URI):

    implements(IRDFURIRefField)

    _type = URIRef

    def __init__(self, prop, **kw):
        super(RDFURIRefField, self).__init__(**kw)
        # TODO: should type chek prop here. (how is z3c doing this? with FieldProperty?)
        #       -> also check if __name__ is useful in case of ordf's ORM
        #       -> name might also be used as ID combined with default namespace
        self.prop = prop

    def fromUnicode(self, str):
        value = URIRef(str)
        self.validate(value)
        return value


class RDFMultiValueField(List):

    implements(IRDFMultiValueField)

    def __init__(self, prop, **kw):
        super(RDFMultiValueField, self).__init__(**kw)
        # TODO: should type chek prop here. (how is z3c doing this? with FieldProperty?)
        #       -> also check if __name__ is useful in case of ordf's ORM
        #       -> name might also be used as ID combined with default namespace
        self.prop = prop

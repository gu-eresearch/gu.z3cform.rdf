import re
from zope.interface import implementer
from zope.schema import Text, List, TextLine, Choice, Field, Orderable
from zope.schema.fieldproperty import FieldProperty
from zope.schema.interfaces import IObject, IDate, WrongType
from rdflib import Literal, URIRef, XSD
from rdflib.util import from_n3
from gu.z3cform.rdf.interfaces import IRDFN3Field, IRDFMultiValueField
from gu.z3cform.rdf.interfaces import IRDFLiteralField, IRDFLiteralLineField
from gu.z3cform.rdf.interfaces import IRDFURIRefField, IRDFChoiceField
from gu.z3cform.rdf.interfaces import IRDFObjectPropertyField, IRDFDateField
from gu.z3cform.rdf.interfaces import IRDFDateRangeField, IRDFField
from gu.z3cform.rdf.vocabulary import SparqlTreeVocabularyFactory
from ordf.namespace import DC
from gu.z3cform.rdf._bootstrap import URIRefField
from gu.z3cform.rdf.utils import Period

# TODO: for specialised fields like URIRef, or Literal field:
#       in case there is data in the graph, that does not match the type
#       leave the data untouched (don't display, and don't change/edit/delete
#       if possible)


@implementer(IRDFN3Field)
class RDFN3Field(Text):
    """
    A field that knows how to handle n3 formatted values.
    """

    _type = (Literal, URIRef)

    prop = FieldProperty(IRDFField['prop'])

    def __init__(self, prop, **kw):
        super(RDFN3Field, self).__init__(**kw)
        # TODO:
        #       -> also check if __name__ is useful in case of ordf's ORM
        #       -> name might also be used as ID combined with default
        #          namespace
        self.prop = prop

    def fromUnicode(self, str):
        value = from_n3(str)
        self.validate(value)
        return value


@implementer(IRDFLiteralField)
class RDFLiteralField(Text):

    _type = Literal

    prop = FieldProperty(IRDFField['prop'])
    rdftype = FieldProperty(IRDFLiteralField['rdftype'])
    rdflang = FieldProperty(IRDFLiteralField['rdflang'])

    def __init__(self, prop, rdftype=None, rdflang=None, **kw):
        super(RDFLiteralField, self).__init__(**kw)
        self.prop = prop
        self.rdftype = rdftype
        self.rdflang = rdflang

    def fromUnicode(self, str):
        # TODO: ensure only rdftype or rdflang is given and use these values in
        #       fromUnicode or is from_n3 more appropriate?
        value = Literal(str)
        self.validate(value)
        return value

    # validate type and lang?


@implementer(IRDFLiteralLineField)
class RDFLiteralLineField(TextLine):

    _type = Literal

    prop = FieldProperty(IRDFField['prop'])
    rdftype = FieldProperty(IRDFLiteralLineField['rdftype'])
    rdflang = FieldProperty(IRDFLiteralLineField['rdflang'])

    def __init__(self, prop, rdftype=None, rdflang=None, **kw):
        super(RDFLiteralLineField, self).__init__(**kw)
        # TODO: ensure only rdftype or rdflang is given and use these values in
        #       fromUnicode
        self.prop = prop
        self.rdftype = rdftype
        self.rdflang = rdflang

    def fromUnicode(self, str):
        # TODO: do from_n3 or apply lang, type to literal
        value = Literal(str)
        self.validate(value)
        return value

    def _validate(self, value):
        super(RDFLiteralLineField, self)._validate(value)
        if value.datatype != self.rdftype:
            raise WrongType(value, self.rdftype, self.__name__)
        # validate type and lang?
        # TODO: validate 00 values?


is_w3cdate = re.compile(r'^\d\d\d\d(-\d\d){0,2}$').match


# TODO: support dcterms:W3CDTF and dcterms:Period? Date? free form data
@implementer(IRDFDateField, IDate)
class RDFDateField(Orderable, RDFLiteralLineField):
    """
    Stores dates in dcterms:W3CDTF format.
    YYYY
    YYYY-MM
    YYYY-MM-DD
    """

    def __init__(self, prop, rdftype=DC['W3CDTF'], **kw):
        super(RDFDateField, self).__init__(prop=prop, rdftype=rdftype, **kw)
        # TODO: ensure rdftype is given and rdflang is none

    def fromUnicode(self, str):
        value = Literal(str, datatype=self.rdftype)
        self.validate(value)
        return value

    def _validate(self, value):
        super(RDFDateField, self)._validate(value)
        if value is not None and not is_w3cdate(value):
            raise ValueError(value, "not a valid W3CDTF date", self.__name__)
        # TODO: use this r'^(\d\d\d\d)(-(\d\d))?(-(\d\d))?$'
        #       and validate number ranges of match.groups(0,2,3)


@implementer(IRDFDateRangeField)
class RDFDateRangeField(RDFLiteralLineField):
    """
    Stores date ranges/ time intervals in dcterms:Period format

    start: W3CDTF end: W3CDTF scheme:W3C-DTF name:Name of Period
    """

    rdftype = FieldProperty(IRDFDateRangeField['rdftype'])

    def __init__(self, prop, rdftype=DC['Period'], **kw):
        super(RDFDateRangeField, self).__init__(prop=prop, rdftype=rdftype, **kw)
        # TODO: ensure only rdftype or rdflang is given and use these values in
        #       fromUnicode

    def fromUnicode(self, str):
        value = Literal(str, datatype=self.rdftype)
        self.validate(value)
        return value

    def _validate(self, value):
        super(RDFDateRangeField, self)._validate(value)
        p = Period(value)
        # Default scheme is W3C-DTF
        if p.scheme is None or p.scheme == 'W3C-DTF':
            if value is not None and (p.start is None and p.end is None):
                raise ValueError(value, "not a valid W3CDTF start or end date", self.__name__)
            if p.start is not None and not is_w3cdate(p.start):
                raise ValueError(value, "not a valid W3CDTF start date", self.__name__)
            if p.end is not None and not is_w3cdate(p.end):
                raise ValueError(value, "not a valid W3CDTF end date", self.__name__)
        # TODO: other validations possible?


@implementer(IRDFURIRefField)
class RDFURIRefField(URIRefField):

    prop = FieldProperty(IRDFField['prop'])

    def __init__(self, prop, **kw):
        super(RDFURIRefField, self).__init__(**kw)
        # TODO:
        #       -> also check if __name__ is useful in case of ordf's ORM
        #       -> name might also be used as ID combined with default
        #          namespace
        self.prop = prop


@implementer(IRDFMultiValueField)
class RDFMultiValueField(List):

    prop = FieldProperty(IRDFField['prop'])

    def __init__(self, prop, **kw):
        super(RDFMultiValueField, self).__init__(**kw)
        # TODO:
        #       -> also check if __name__ is useful in case of ordf's ORM
        #       -> name might also be used as ID combined with default
        #          namespace
        self.prop = prop


@implementer(IRDFChoiceField)
class RDFURIChoiceField(Choice):

    prop = FieldProperty(IRDFField['prop'])

    def __init__(self, prop, **kw):
        super(RDFURIChoiceField, self).__init__(**kw)
        self.prop = prop


@implementer(IRDFChoiceField)
class RDFGroupedURIChoiceField(Choice):
    # FIXME: have a separate class now for tree vocabulary backed field ...
    #        can register default widget for it.

    prop = FieldProperty(IRDFField['prop'])

    def __init__(self, prop, classuri, **kw):
        kw['vocabulary'] = SparqlTreeVocabularyFactory(classuri)()
        super(RDFGroupedURIChoiceField, self).__init__(**kw)
        self.prop = prop


@implementer(IRDFObjectPropertyField)
class RDFObjectPropertyField(RDFURIRefField):

    def _validate(self, value):
        super(RDFObjectPropertyField, self)._validate(value)

        # schema has to be provided by value
        # if not self.schema.providedBy(value):
        #     raise SchemaNotProvided

        # # check the value against schema
        # errors = _validate_fields(self.schema, value)
        # if errors:
        #     raise WrongContainedType(errors, self.__name__)

    def set(self, object, value):
        # Announce that we're going to assign the value to the object.
        # Motivation: Widgets typically like to take care of policy-specific
        # actions, like establishing location.
        # event = BeforeObjectAssignedEvent(value, self.__name__, object)
        # notify(event)
        # # The event subscribers are allowed to replace the object, thus we
        # # need to replace our previous value.
        #value = event.object
        import ipdb; ipdb.set_trace()
        super(RDFObjectPropertyField, self).set(object, value)

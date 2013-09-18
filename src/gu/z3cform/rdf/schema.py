from zope.interface import implementer
from zope.schema import Text, List, TextLine, Choice, Field, Date
from zope.schema.fieldproperty import FieldProperty
from zope.schema.interfaces import IObject
from rdflib import Literal, URIRef, XSD
from rdflib.util import from_n3
from gu.z3cform.rdf.interfaces import IRDFN3Field, IRDFMultiValueField
from gu.z3cform.rdf.interfaces import IRDFLiteralField, IRDFLiteralLineField
from gu.z3cform.rdf.interfaces import IRDFURIRefField, IRDFChoiceField
from gu.z3cform.rdf.interfaces import IRDFObjectField, IRDFDateField
from gu.z3cform.rdf.interfaces import IRDFDateRangeField, IRDFField
from gu.z3cform.rdf.vocabulary import SparqlTreeVocabularyFactory
from ordf.namespace import DC
from gu.z3cform.rdf._bootstrap import URIRefField

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
        #       fromUnicode
        value = Literal(str)
        self.validate(value)
        return value


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
        value = Literal(str)
        self.validate(value)
        return value


@implementer(IRDFDateField)
class RDFDateField(Date):

    prop = FieldProperty(IRDFField['prop'])
    rdftype = FieldProperty(IRDFDateField['rdftype'])

    def __init__(self, prop, **kw):
        super(RDFDateField, self).__init__(**kw)
        # TODO: ensure only rdftype or rdflang is given and use these values in
        #       fromUnicode
        self.prop = prop
        self.rdftype = XSD['date']

    def fromUnicode(self, str):
        value = Literal(str, datatype=self.rdftype)
        self.validate(value)
        return value

    def validate(self, value):
        # TODO: fix this validation. is it really necessary to convert again to a python object?
        if value is not None:
            value = value.toPython()
        return super(RDFDateField, self).validate(value)

    def get(self, object):
        import ipdb; ipdb.set_trace()
        return super(RDFDateField, self).get(object)

    def query(self, object, default=None):
        import ipdb; ipdb.set_trace()
        return super(RDFDateField, self).query(object, default)

    def set(self, object, value):
        import ipdb; ipdb.set_trace()
        super(RDFDateField, self).set(object, value)


@implementer(IRDFDateRangeField)
class RDFDateRangeField(RDFN3Field):

    prop = FieldProperty(IRDFField['prop'])
    rdftype = FieldProperty(IRDFDateRangeField['rdftype'])

    def __init__(self, prop, **kw):
        super(RDFDateRangeField, self).__init__(prop=prop, **kw)
        # TODO: ensure only rdftype or rdflang is given and use these values in
        #       fromUnicode
        self.rdftype = DC['Period']

    def fromUnicode(self, str):
        value = Literal(str, datatype=self.rdftype)
        self.validate(value)
        return value

    def validate(self, value):
        # TODO: fix this validation. is it really necessary to convert again to a python object?
        #if value is not None:
        #    value = value.toPython()
        return super(RDFDateRangeField, self).validate(value)


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
    #        can register default widget for it. (don't need widgetFactory
    #        in fresnel defs.)

    prop = FieldProperty(IRDFField['prop'])

    def __init__(self, prop, classuri, **kw):
        kw['vocabulary'] = SparqlTreeVocabularyFactory()(classuri)
        super(RDFGroupedURIChoiceField, self).__init__(**kw)
        self.prop = prop


@implementer(IRDFObjectField, IObject)
class RDFObjectField(Field):
    # Implement IObject to trigger special handling on
    # z3c.form.form.applyChanges

    prop = FieldProperty(IRDFField['prop'])

    classuri = FieldProperty(IRDFObjectField['classuri'])

    def __init__(self, prop, **kw):  # classuri, **kw):
        self.classuri = kw.pop('classuri', None)
        super(RDFObjectField, self).__init__(**kw)
        self.prop = prop

    def _validate(self, value):
        super(RDFObjectField, self)._validate(value)

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
        super(RDFObjectField, self).set(object, value)





#         <configure
#     xmlns="http://namespaces.zope.org/zope"
#     xmlns:z3c="http://namespaces.zope.org/z3c"
#     i18n_domain="z3c.form">

#   <class class=".object.ObjectWidget">
#     <require
#         permission="zope.Public"
#         interface="z3c.form.interfaces.IObjectWidget"
#         />
#   </class>

#   <adapter
#       factory=".object.ObjectFieldWidget"
#       for="zope.schema.interfaces.IObject
#            z3c.form.interfaces.IFormLayer"
#       />

#   <z3c:widgetTemplate
#       mode="display"
#       widget="z3c.form.interfaces.IObjectWidget"
#       layer="z3c.form.interfaces.IFormLayer"
#       template="object_display.pt"
#       />

#   <z3c:widgetTemplate
#       mode="input"
#       widget="z3c.form.interfaces.IObjectWidget"
#       layer="z3c.form.interfaces.IFormLayer"
#       template="object_input.pt"
#       />

#   <z3c:widgetTemplate
#       mode="hidden"
#       widget="z3c.form.interfaces.IObjectWidget"
#       layer="z3c.form.interfaces.IFormLayer"
#       template="object_input.pt"
#       />

# </configure>

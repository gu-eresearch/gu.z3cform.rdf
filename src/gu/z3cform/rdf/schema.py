from zope.interface import implements
from zope.schema import Text, List, TextLine, URI, Choice, Set, Field
from rdflib import Literal, URIRef
from rdflib.util import from_n3
from gu.z3cform.rdf.interfaces import IRDFN3Field, IRDFMultiValueField
from gu.z3cform.rdf.interfaces import IRDFLiteralField, IRDFLiteralLineField
from gu.z3cform.rdf.interfaces import IRDFURIRefField, IRDFChoiceField
from gu.z3cform.rdf.interfaces import IRDFObjectField
from gu.z3cform.rdf.vocabulary import SparqlVocabularyFactory, SparqlTreeVocabularyFactory

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


class RDFLiteralField(Text):

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


class RDFLiteralLineField(TextLine):

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


class RDFURIChoiceField(Choice):

    implements(IRDFChoiceField)

    def __init__(self, prop, classuri, **kw):
        kw['vocabulary'] = SparqlVocabularyFactory()(classuri)
        super(RDFURIChoiceField, self).__init__(**kw)
        self.prop = prop


class RDFGroupedURIChoiceField(Choice):
    # FIXME: have a separate class now for tree vocabulary backed field ... can register default widget for it. (don't need widgetFactory in fresnel defs.)

    implements(IRDFChoiceField)

    def __init__(self, prop, classuri, **kw):
        kw['vocabulary'] = SparqlTreeVocabularyFactory()(classuri)
        super(RDFGroupedURIChoiceField, self).__init__(**kw)
        self.prop = prop

from zope.schema.interfaces import IObject

class RDFObjectField(Field):
    # Implement IObject to trigger special handling on z3c.form.form.applyChanges
    
    implements(IRDFObjectField, IObject)

    classuri = None

    def __init__(self, prop, **kw): #, classuri, **kw):
        #self.classuri = classuri
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
        # # The event subscribers are allowed to replace the object, thus we need
        # # to replace our previous value.
        value = event.object
        import ipdb; ipdb.set_trace()
        super(Object, self).set(object, value)





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

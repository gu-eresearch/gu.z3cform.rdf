from zope.interface import Interface
from zope.schema import List, Object, TextLine
from gu.z3cform.rdf._bootstrap import URIRefField
from rdflib import XSD
from ordf.namespace import DC
# expected to be imported from here
from gu.z3cform.rdf._bootstrap import IURIRef
IURIRef  # make pyflakes happy


class IRDFField(Interface):
    """
    A field managing values in an rdflib Graph.
    """

    prop = URIRefField(
        title=u"URI of RDF property",
        description=u"read and write values to given RDF property"
        )


# TODO: check if we should base all these on an IRDFField base interface?
class IRDFN3Field(IRDFField):
    """
    Field that stores rdflib Literal or URIRef.
    """


class IRDFDataPropertyField(IRDFField):

    rdftype = URIRefField(
        title=u"Literal datatype",
        required=False
        )

    rdflang = TextLine(
        title=u"Literal language",
        required=False
        )


class IRDFObjectPropertyField(IRDFField):

    pass


class IRDFMultiValueField(IRDFField):
    """Field that stores a multiple values of the same property.

    value_type should be an IRDFField, otherwise serialisation to RDF
    might not work properly.  (TODO: to solve this could make Field
    implementation more intelligent to convert to Literal, URIRef if
    appropriate)

    """


class IRDFLiteralField(IRDFDataPropertyField):
    """
    A field handling multiline rdflib Literals
    """


class IRDFLiteralLineField(IRDFDataPropertyField):
    """
    A field handling rdflib Literals
    """


class IRDFDateField(IRDFDataPropertyField):
    """

    Class: IRDFDateField

    [IRDFDateField description]

    TODO: check whether this is better be
    solved via a typed IRDFLiteralLineField (rdflib would support
    casting between string and actual python field value)
    TODO: default to dcterms:W3CDTF?

    """

    rdftype = URIRefField(
        title=u"Literal datatype",
        required=False,
        default=DC['W3CDTF']
        )


class IRDFDateRangeField(IRDFDataPropertyField):
    """

    Class: IRDFDateRangeField

    [IRDFDateRangeField description]


    Extends: IRDFField
    """

    rdftype = URIRefField(
        title=u"Literal datatype",
        required=False,
        default=DC['Period']
        )


class IRDFURIRefField(IRDFDataPropertyField):
    """
    A field handling rdflib URIRefs

    TODO: might be nice to support RDF Classes, or SPARQL queries here
          to restrict the set of elements that can be linked.
    """
    pass


class IRDFChoiceField(IRDFDataPropertyField):
    """
    A field handling rdflib URIRefs

    TODO: might be nice to support RDF Classes, or SPARQL queries here
          to restrict the set of elements that can be linked.
    """
    pass


class IRDFObjectField(IRDFObjectPropertyField):
    """
    A field handling rdflib URIRefs

    TODO: might be nice to support RDF Classes, or SPARQL queries here
          to restrict the set of elements that can be linked.
    """

    # TODO: rename to range?
    classuri = URIRefField(
        title=u'Class URI',
        required=True,
        )


# Tools and objects

class IORDF(Interface):
    """
    Utility interface to get configured ORDF handler.
    """

    def getHandler():
        """
        return an initialised ORDF handler.
        """

    def getFresnel():
        """ return a pre-compiled Fresnel implementation """

    def getBaseURI():
        """ return the base uri to be used for all content """

    def generateURI():
        """ generate a new unique uri using base uri """


class IGraph(Interface):

    pass


class IIndividual(Interface):
    """
    An RDF / OWL individual
    """

    identifier = URIRefField(
        title=u"Identifier",
        description=u"The URI for this individual."
        )

    graph = Object(
        title=u"Graph",
        description=u"The store for this individual.",
        schema=IGraph
        )

    type = List(
        title=u"Type",
        description=u"The RDF / OWL type for this individual.",
        value_type=URIRefField()
        )

    sameAs = Object(
        title=u"Same As",
        description=u"Same As Individuals",
        schema=Interface  # IIndividual
        )


class IRDFTypeMapper(Interface):

    def applyTypes(graph):
        """
        update rdf:type information in graph
        """


class IFresnelVocabularyFactory(Interface):
    """
    Marker interface for vocabulary factories registered via Fresnel.
    """

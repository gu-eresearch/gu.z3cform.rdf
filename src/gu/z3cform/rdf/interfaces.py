from zope.schema.interfaces import IText


class IRDFN3Field(IText):
    """
    Field that stores rdflib Literal or URIRef.
    """

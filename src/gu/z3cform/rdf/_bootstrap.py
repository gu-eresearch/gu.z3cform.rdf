from zope.interface import implementer
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import INativeStringLine
from zope.schema.interfaces import InvalidURI
from zope.schema import NativeStringLine
from rdflib.term import _is_valid_uri
from rdflib import URIRef


class IURIRef(INativeStringLine):
    """A field containing an URI
    """

    pass


@implementer(IURIRef, IFromUnicode)
class URIRefField(NativeStringLine):
    # can't subclass from schema.URI as it validates to be a URL,
    # but a URI is more generic

    _type = URIRef

    def _validate(self, value):
        super(URIRefField, self)._validate(value)

        if not _is_valid_uri(value):
            raise InvalidURI(value)

    def fromUnicode(self, value):
        v = URIRef(value.strip())
        self._validate(v)
        return v

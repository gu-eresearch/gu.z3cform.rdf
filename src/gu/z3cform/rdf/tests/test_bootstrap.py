import unittest2 as unittest
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from zope.schema.interfaces import WrongType
from zope.schema.interfaces import ConstraintNotSatisfied
from zope.schema.interfaces import InvalidURI
from gu.z3cform.rdf.interfaces import IURIRef
from gu.z3cform.rdf.schema import URIRefField
from rdflib import URIRef


class URIRefFieldTest(unittest.TestCase):

    def _getTargetClass(self):
        return URIRefField

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IURIRef(self):
        verifyClass(IURIRef, self._getTargetClass())

    def test_instance_conforms_to_IURIRef(self):
        verifyObject(IURIRef, self._makeOne())

    def test_validate_wrong_types(self):
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_a_uri(self):
        field = self._makeOne()
        self.assertRaises(InvalidURI, field.validate, URIRef(u'urn:<invalid>'))
        self.assertRaises(ConstraintNotSatisfied,
                          field.validate, URIRef(u'http://example.com/\nDAV:'))

    def test_fromUnicode_ok(self):
        field = self._makeOne()
        self.assertEqual(field.fromUnicode(u'http://example.com/'),
                         URIRef(u'http://example.com/'))

    def test_fromUnicode_invalid(self):
        field = self._makeOne()
        self.assertRaises(InvalidURI, field.fromUnicode, u'urn:<invalid>')
        self.assertRaises(ConstraintNotSatisfied,
                          field.fromUnicode, u'http://example.com/\nDAV:')

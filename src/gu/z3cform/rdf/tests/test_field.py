import unittest
from rdflib import URIRef, Literal, BNode, Namespace

EX = Namespace('http://example.com/namespace#')

class RDFN3Test(unittest.TestCase):

    def _getTargetClass(self):
        from gu.z3cform.rdf.schema import RDFN3Field
        return RDFN3Field

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(prop=EX['prop'], *args, **kw)

    def test_validate_wrong_types(self):
        from zope.schema.interfaces import WrongType
        from zope.schema._compat import b
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, b(''))
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_w_invalid_default(self):
        from zope.schema._compat import b
        from zope.schema.interfaces import ValidationError
        self.assertRaises(ValidationError, self._makeOne, default=b(''))

    def test_validate_not_required(self):
        from zope.schema._compat import u
        field = self._makeOne(required=False)
        field.validate(Literal(u('')))
        field.validate(Literal(u('abc')))
        field.validate(Literal(u('abc\ndef')))
        field.validate(None)

    def test_validate_required(self):
        from zope.schema.interfaces import RequiredMissing
        from zope.schema._compat import u
        field = self._makeOne()
        field.validate(Literal(u('')))
        field.validate(Literal(u('abc')))
        field.validate(Literal(u('abc\ndef')))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_fromUnicode_miss(self):
        from zope.schema._bootstrapinterfaces import WrongType
        from zope.schema._compat import b
        deadbeef = b('<DEADBEEF>')
        txt = self._makeOne()
        self.assertRaises(WrongType, txt.fromUnicode, URIRef(b('DEADBEEF')))

    def test_fromUnicode_hit(self):
        from zope.schema._compat import u
        deadbeef = u('<DEADBEEF>')
        txt = self._makeOne()
        self.assertEqual(txt.fromUnicode(deadbeef), URIRef(u('DEADBEEF')))

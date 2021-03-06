import unittest
from rdflib import URIRef, Literal, Namespace
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from zope.schema.interfaces import IText
from zope.schema.interfaces import RequiredMissing
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import WrongType
from gu.z3cform.rdf.interfaces import IRDFN3Field


EX = Namespace('http://example.com/namespace#')


class RDFN3Test(unittest.TestCase):

    def _getTargetClass(self):
        from gu.z3cform.rdf.schema import RDFN3Field
        return RDFN3Field

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(prop=EX['prop'], *args, **kw)

    def test_class_conforms_to_IDate(self):
        klass = self._getTargetClass()
        verifyClass(IText, klass)
        verifyClass(IRDFN3Field, klass)

    def test_instance_conforms_to_IDate(self):
        field = self._makeOne()
        verifyObject(IText, field)
        verifyObject(IRDFN3Field, field)

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

    def test_validate_w_invalid_default(self):
        self.assertRaises(ValidationError, self._makeOne, default=b'')

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(Literal(u''))
        field.validate(Literal(u'abc'))
        field.validate(Literal(u'abc\ndef'))
        field.validate(None)

    def test_validate_required(self):
        field = self._makeOne()
        field.validate(Literal(u''))
        field.validate(Literal(u'abc'))
        field.validate(Literal(u'abc\ndef'))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_fromUnicode_miss(self):
        txt = self._makeOne()
        self.assertRaises(WrongType, txt.fromUnicode, u'DEADBEEF')

    def test_fromUnicode_hit(self):
        deadbeef = u'<DEADBEEF>'
        txt = self._makeOne()
        self.assertEqual(txt.fromUnicode(deadbeef), URIRef(u'DEADBEEF'))

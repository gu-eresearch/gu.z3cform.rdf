import unittest
from rdflib import URIRef, Literal, Namespace
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from zope.schema.interfaces import RequiredMissing
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import WrongType
from gu.z3cform.rdf.interfaces import IRDFDateRangeField
from gu.z3cform.rdf.schema import RDFDateRangeField

EX = Namespace(u'http://example.com/namespace#')
DT = URIRef(u'http://purl.org/dc/terms/Period')


class RDFDateRangeTest(unittest.TestCase):

    def _getTargetClass(self):
        return RDFDateRangeField

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(prop=EX['prop'], *args, **kw)

    def test_class_conforms_to_Interface(self):
        verifyClass(IRDFDateRangeField, self._getTargetClass())

    def test_instance_conforms_to_Interface(self):
        verifyObject(IRDFDateRangeField, self._makeOne())

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
        self.assertRaises(ValidationError, self._makeOne, default='')

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(Literal(u'start=1991;', datatype=DT))
        field.validate(Literal(u'start=1991-10;', datatype=DT))
        field.validate(Literal(u'start=1991; end=1991;', datatype=DT))
        field.validate(Literal(u'start=1991-10; end=1991-10;', datatype=DT))
        field.validate(Literal(u'start=1991; end=1991; scheme=W3C-DTF;', datatype=DT))
        field.validate(Literal(u'start=1991-10; end=1991-10; scheme=W3C-DTF;', datatype=DT))
        field.validate(Literal(u'start=Cambrian period; scheme=Geological timescale; name=Phanerozoic Eon;', datatype=DT))
        field.validate(None)

    def test_validate_required(self):
        field = self._makeOne()
        field.validate(Literal(u'start=1991;', datatype=DT))
        field.validate(Literal(u'start=1991-10;', datatype=DT))
        field.validate(Literal(u'start=1991; end=1991;', datatype=DT))
        field.validate(Literal(u'start=1991-10; end=1991-10;', datatype=DT))
        field.validate(Literal(u'start=1991; end=1991; scheme=W3C-DTF;', datatype=DT))
        field.validate(Literal(u'start=1991-10; end=1991-10; scheme=W3C-DTF;', datatype=DT))
        field.validate(Literal(u'start=Cambrian period; scheme=Geological timescale; name=Phanerozoic Eon;', datatype=DT))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_fromUnicode_miss(self):
        field = self._makeOne()
        self.assertRaises(ValueError, field.fromUnicode, u'')
        self.assertRaises(ValueError, field.fromUnicode, u'start=Cambrian period; name=Phanerozoic Eon;')

    def test_fromUnicode_hit(self):
        deadbeef = u'start=1991;'
        field = self._makeOne()
        self.assertEqual(field.fromUnicode(deadbeef), Literal(u'start=1991;', datatype=DT))

    def test_validate_dates(self):
        field = self._makeOne()
        self.assertRaises(ValueError, field.validate, Literal(u'start=1991-01-01T;', datatype=DT))
        self.assertRaises(ValueError, field.validate, Literal(u'start=1991:01:01;', datatype=DT))
        self.assertRaises(ValueError, field.validate, Literal(u'start=199;', datatype=DT))
        self.assertRaises(ValueError, field.validate, Literal(u'start=1991-1;', datatype=DT))
        self.assertRaises(ValueError, field.validate, Literal(u'start=1991-01-1;', datatype=DT))
        field.validate(Literal(u'start=1991-01-01;', datatype=DT))
        self.assertRaises(WrongType, field.validate, Literal(u'start=1991-01-01;'))
        self.assertRaises(WrongType, field.validate, Literal(u'start=1991-01-01;', datatype=EX['date']))

from zope.component import getUtility, getMultiAdapter
from z3c.form.interfaces import IWidget, NO_VALUE, IDataManager
from z3c.form.converter import BaseDataConverter
from rdflib.util import from_n3
from ordf.graph import Graph, _Graph
from gu.z3cform.rdf.interfaces import (IRDFN3Field, IRDFObjectField,
                                       IRDFTypeMapper)
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectWidget
from gu.z3cform.rdf.fresnel import getFieldsFromFresnelLens
from gu.z3cform.rdf.interfaces import IORDF
from z3c.form.object import ObjectSubForm
from zope.interface import implementer
from zope.component import adapter
from z3c.form.field import Fields
from ordf.namespace import FRESNEL
from rdflib import RDF
from zope.schema.interfaces import ICollection


@adapter(IRDFN3Field, IWidget)
class RDFN3DataConverter(BaseDataConverter):
    """
    use rdflibs n3 parser/generator to convert values.

    This converter accepts an n3 formatted object value and converts it into an
    rdflib Node instance.
    """

    def __init__(self, field, widget):
        self.field = field
        self.widget = widget

    def toFieldValue(self, value):
        if value == u'':
            return self.field.missing_value
        return from_n3(value)

    def toWidgetValue(self, value):
        if value is None:
            return None
        return value.n3()


@adapter(IRDFObjectField, IRDFObjectWidget)
class RDFObjectConverter(BaseDataConverter):
    """Data converter for IObjectWidget."""

    def toWidgetValue(self, value):
        """Just dispatch it."""
        # value sholud always be a Graph here

        # There is an asymmetry here. toWidgetValue get's a graph and
        # passes this graph on to the widget. The widget is expected
        # to work from the graph directly.
        # However, when the widget processes a request it generates a
        # dictionary as value, which will be passed into toFieldValue.
        # Unfortunatel we can't just generate a dictionary here, because
        # we don't know yet the fields in the widgets subform. Without fields
        # we have no clue which values to map to which field names.

        if value is self.field.missing_value:
            return NO_VALUE  # TODO: empty graph here?
        return value

        # TODO: The code below does not work properly.
        # It probably needs a datamanager for rdffields, that can work
        # on dictionaries

        # could look into lens to get fields (self.field.lens)
        # get FieldsFromLens ... plus self.field.schema?

        # retval = {}
        # groups, fields = getFieldsFromFresnelLens(self.field.lens, value,
        #                                           value.identifier)
        # for field in fields:
        #     dm = getMultiAdapter(
        #         (value, field), IDataManager)
        #     retval[field.__name__] = dm.query()
        # return retval

    def createObject(self, value):
        # This is being used by toFieldValue. We ignore the value
        # here and let toFieldValue apply whatever necessary
        ordftool = getUtility(IORDF)
        identifier = ordftool.generateURI()
        obj = Graph(identifier=identifier)
        return obj

    def toFieldValue(self, value):
        """field value is an Object type, that provides field.schema"""
        # we should always get a dict as value here
        if value is NO_VALUE:
            return self.field.missing_value

        if self.widget.subform is None:
            # creepy situation when the widget is hanging in nowhere
            obj = self.createObject(value)
        else:
            if self.widget.subform.ignoreContext:
                obj = self.createObject(value)
            else:
                dm = getMultiAdapter(
                    (self.widget.context, self.field), IDataManager)
                try:
                    # we should get the sub object from the same graph
                    data = dm.get()
                    # have to make a copy here, so that form apply can
                    # compare to the originally retrieved graph
                    obj = Graph(identifier=data.identifier)
                    # TODO: make it quad aware
                    for t in data:
                        obj.add(t)
                except KeyError:
                    obj = self.createObject(value)
                except AttributeError:
                    obj = self.createObject(value)

        if obj is None or obj == self.field.missing_value:
            # if still None create one, otherwise following will burp
            obj = self.createObject(value)

        # apply rdf:type from Lens
        # TODO: maybe datamanager could do this?
        #       here it assumes there is a classLensDomain in use
        lens = self.widget.field.lens
        rdftype = lens.value(lens.identifier, FRESNEL['classLensDomain'])
        obj.add((obj.identifier, RDF['type'], rdftype))

        # TODO: should get fields from lens instead of subform
        for name in self.widget.subform.fields:
            try:
                field = self.widget.subform.fields[name].field
                data = value[name]
                if not ICollection.providedBy(field):
                    data = [data]
                for val in data:
                    obj.remove((obj.identifier, field.prop, None))
                    if val is not None:
                        obj.add((obj.identifier, field.prop, val))
            except KeyError:
                pass
        # TODO: where am I going to do the ObjectModified event with subforms?

        # Commonly the widget context is security proxied. This method,
        # however, should return a bare object, so let's remove the
        # security proxy now that all fields have been set using the security
        # mechanism.
        # return removeSecurityProxy(obj)

        return obj


# TODO: move somewhere else
class RDFObjectSubForm(ObjectSubForm):

    def setupFields(self):
        context = self.getContent()
        lens = self.__parent__.field.lens
        if lens is not None:
            _, fields = getFieldsFromFresnelLens(lens, context,
                                                 context.identifier)
            self.fields = Fields(*fields)
        else:
            self.fields = Fields()

    def getContent(self):
        val = self.__parent__._value
        if val == NO_VALUE:
            return Graph()
        if not isinstance(val, _Graph):
            return Graph()
        return val


# TODO: move somewhere else
@implementer(IRDFTypeMapper)
class RDFTypeMapper(object):

    def __init__(self, context, request, form):
        self.context = context
        self.request = request
        self.form = form

    def applyTypes(self, graph):
        graph.add((graph.identifier, RDF['type'], self.form.rdftype))

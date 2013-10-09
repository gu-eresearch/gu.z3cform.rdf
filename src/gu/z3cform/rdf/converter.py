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
from rdflib import RDF, URIRef
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


        # TODO: The widget does'nt work with dictionaries.
        # It probably needs a datamanager for rdffields, that can work
        # on dictionaries

        lens = self.widget.field.lens
        # TODO: what about groups in object subforms?
        _, fields = getFieldsFromFresnelLens(lens, value, value.identifier)

        widget_value = {}
        for name in fields:
            field = fields[name].field
            data = list(value.objects(value.identifier, field.prop))
            if not data:
                widget_value[name] = None
            elif not ICollection.providedBy(field):
                widget_value[name] = data[0]
            else:
                widget_value[name] = data
        if isinstance(value.identifier, URIRef):
            widget_value['identifier'] = value.identifier
        return widget_value



    def createObject(self, value):
        # This is being used by toFieldValue.
        # We genarete a new graph with an identifier and let toFieldValue
        # apply the rest

        # use identifier from value or generate new identifier
        # TODO: maybe do BNode here and let dm take care of generating URI?
        identifier = value.get('identifier')
        if not identifier:
            identifier = getUtility(IORDF).generateURI()
        else:
            identifier = URIRef(identifier)
        obj = Graph(identifier=identifier)
        return obj

    def toFieldValue(self, value):
        """field value is an Object type, that provides field.schema"""
        # we should always get a dict as value here
        if isinstance(value, Graph):
            # this happens in case we have a multi object widget. when setting a new value to MultiWidget and MultiWidget applying all values to sub forms
            # TODO: just pass through for now
            return value
        if value is NO_VALUE:
            return self.field.missing_value

        if self.widget.subform is None:
            # creepy situation when the widget is hanging in nowhere
            obj = self.createObject(value)
        else:
            if self.widget.subform.ignoreContext:
                obj = self.createObject(value)
            else:
                # This usually fails for multi objecwidget, as we don't really know
                # which one of of multiple subgraphs to load
                dm = getMultiAdapter(
                    (self.widget.subform.context, self.field), IDataManager)
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

        # Have to get the fields for lens, as multi widget does not do a widget update
        # before calling toFieldValue
        _, fields = getFieldsFromFresnelLens(lens, obj, obj.identifier)

        for name in fields:
            try:
                data = value[name]
                if data is None:
                    # ignore None values
                    continue
                field = fields[name].field
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
            _, self.fields = getFieldsFromFresnelLens(lens, context,
                                                 context.identifier)
        else:
            # TODO: raise error here?, without lens we can't do much
            self.fields = Fields()

        from zope.schema import TextLine
        from z3c.form.interfaces import HIDDEN_MODE
        idfields = Fields(TextLine(__name__='identifier',
                                   readonly=True,
                                   required=False))
        idfields['identifier'].mode = HIDDEN_MODE
        self.fields += idfields

    def getContent(self):
        # if the widget set a context for use, try to use it
        #    otherwise use the widget value
        if not self.ignoreContext and self.context:
            val = self.context
        else:
            val = self.__parent__._value
        if val == NO_VALUE:
            return Graph()
        if not isinstance(val, _Graph):
            # usually a dict with extracted widget_value
            # TODO: convert to fieldvalue here? Might make the toFieldValue to dict work again
            identifier = val.get('identifier')
            if identifier:
                identifier = URIRef(identifier)
            return Graph(identifier=identifier)
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

from zope.component import adapts, getUtility
import zope.schema.interfaces
from z3c.form.interfaces import IWidget, NO_VALUE, IDataManager
from z3c.form.converter import BaseDataConverter
from rdflib.util import from_n3
from ordf.graph import Graph, _Graph
from gu.z3cform.rdf.interfaces import IRDFN3Field, IRDFObjectField, IRDFTypeMapper
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectWidget
from gu.z3cform.rdf.fresnel import getFieldsFromFresnelLens
from gu.z3cform.rdf.interfaces import IORDF
from z3c.form.object import ObjectSubForm
import zope.interface
import zope.schema
from zope.interface import implementer
from z3c.form.field import Fields
import zope.component
from ordf.namespace import FRESNEL
from rdflib import RDF


class RDFN3DataConverter(BaseDataConverter):
    """
    use rdflibs n3 parser/generator to convert values.

    This converter accepts an n3 formatted object value and converts it into an
    rdflib Node instance.
    """

    adapts(IRDFN3Field, IWidget)

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


class RDFObjectConverter(BaseDataConverter):
    """Data converter for IObjectWidget."""

    adapts(IRDFObjectField, IRDFObjectWidget)

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
                dm = zope.component.getMultiAdapter(
                    (self.widget.context, self.field), IDataManager)
                try:
                    # we should get the sub object from the same graph
                    obj = dm.get()
                except KeyError:
                    obj = self.createObject(value)
                except AttributeError:
                    obj = self.createObject(value)

        if obj is None or obj == self.field.missing_value:
            # if still None create one, otherwise following will burp
            obj = self.createObject(value)

        # convert dictionary to graph
        oldval = value
        value = Graph()
        for key, val in oldval.items():
            if val is None: # TODO: also check missing/NO_VALUE?
                continue
            field = self.widget.subform.fields[key]
            # should I check field for ICollection?
            if not isinstance(val, list) and not isinstance(val, tuple):
                value.add((value.identifier, field.field.prop, val))
            else:
                for v in val:
                    value.add((value.identifier, field.field.prop, v))
        # apply rdf:type from Lens
        # TODO: maybe datamanager could do this?
        #       here it assumes there is a classLensDomain in use
        lens = self.widget.field.lens
        rdftype = lens.value(lens.identifier, FRESNEL['classLensDomain'])
        value.add((value.identifier, RDF['type'], rdftype))

        # apply new values and track changed properties
        names = []
        # FIXME: use DataManager possibly loop over all fields?
        # 1. remove changed props from obj (even those that don't exist in value)
        for prop in set(obj.predicates(obj.identifier, None)):
            # TODO: check whethe I am comparing generators here
            #       maybe use set() to compare unordered list?
            if obj.objects(obj.identifier, prop) != value.objects(value.identifier, prop):
                # property has been changed ... remove it
                names.append(prop)
                obj.remove((obj.identifier, prop, None))
        # 2. update possible changes and add new props from value
        # TODO: this looks doubled up to step 1
        for prop in set(value.predicates(value.identifier, None)):
            if obj.objects(obj.identifier, prop) != value.objects(value.identifier, prop):
                if prop not in names:
                    names.append(prop)
                obj.remove((obj.identifier, prop, None))  # should not be necessary here
                for val in value.objects(value.identifier, prop):
                    obj.add((obj.identifier, prop, val))

        #obj = self.field.schema(obj)
        # TODO: when resurrecting the commented code below, be aware that value is arleady a graph
        # names = []
        # for name in self.widget.subform.fields:
        #     try:
        #         # TODO: maybe try te get field from somewhere else ...
        #                 e.g. Lens? we need schema.field not form.field here
        #         dm = zope.component.getMultiAdapter(
        #             (obj, self.widget.subform.fields[name].field),
        #              IDataManager)
        #         oldval = dm.query()
        #         if oldval != value[name]:
        #             dm.set(value[name])
        #             names.append(name)
        #     except KeyError:
        #         pass

        # TODO: notify on changes
        # if names:
        #     zope.event.notify(
        #       zope.lifecycleevent.ObjectModifiedEvent(obj,
        #           zope.lifecycleevent.Attributes(self.field.schema, *names)))

        # Commonly the widget context is security proxied. This method,
        # however, should return a bare object, so let's remove the
        # security proxy now that all fields have been set using the security
        # mechanism.
        # return removeSecurityProxy(obj)
        if len(obj)==0:
            # TODO: if we have an empty graph then return None
            #       or should the datamanager.GraphDataManagerForObjectFields take care of this?
            obj = None
        return obj


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


@implementer(IRDFTypeMapper)
class RDFTypeMapper(object):

    def __init__(self, context, request, form):
        self.context = context
        self.request = request
        self.form = form

    def applyTypes(self, graph):
        graph.add((graph.identifier, RDF['type'], self.form.rdftype))

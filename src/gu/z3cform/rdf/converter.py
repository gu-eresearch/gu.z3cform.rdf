from zope.component import adapts, getUtility
import zope.schema.interfaces
from z3c.form.interfaces import IWidget, NO_VALUE, IDataManager, IDataConverter
from z3c.form.converter import BaseDataConverter
from rdflib.util import from_n3
from rdflib import URIRef
from ordf.graph import Graph, _Graph
from gu.z3cform.rdf.interfaces import IRDFN3Field, IRDFObjectField
# FIXME: this is probably a circular import ...
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectWidget
from gu.z3cform.rdf.fresnel import getFieldsFromFresnelLens
from z3c.form.form import applyChanges
import zope.interface
import zope.schema
from z3c.form.interfaces import ISubForm, IValidator, IErrorViewSnippet
from z3c.form.interfaces import IFormAware
from z3c.form import form
from z3c.form.field import Fields
import zope.component
from zope.schema.interfaces import ICollection


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

        # convert entire value / graph into  a dictionary

        if value is self.field.missing_value:
            return NO_VALUE  # TODO: empty graph here?
        # TODO there is no subform here yet?
        #      z3c.form uses field schema .... we have a lens here
        #      which could help

        # TODO check whether we can get the widget to generate a form earlier?
        #      or does it need the value to use the lens correctly?
        return value

        # TODO shall we convert do dict here, but we don't know the subform yet
        # ret =  {}
        # for field in self.widget.subform.fields.values():
        #     # FIXME... check for field.prefix as well
        #     if ICollection.providedBy(field):
        #         ret[field.__name__] = list(value.objects(value.identifier, field.field.prop))
        #     else:
        #         ret[field.__name__] = value.value(value.identifier, field.field.prop)

        # return ret


            # retval = {}
        # # TODO: LOG this ... try to figure out all calls to _getForm and
        #                      setupFields.
        # #       the fields are defined by the lens + what's available on the
        #         content object. so we can create the subform, and let it do
        #         it's job get a full field list
        # if self.widget.subform is  None:
        #     self.widget._getForm(value)
        #     self.widget.subform.setupFields()
        # for name in self.widget.subform.fields:
        #     # TODO: maybe try te get field from somewhere else ... e.g. Lens?
        #             we need schema.field not form.field here
        #     dm = zope.component.getMultiAdapter(
        #         (value, self.widget.subform.fields[name].field),IDataManager)
        #     retval[name] = dm.query()

        # return retval

    def createObject(self, value):
        #keep value passed, maybe some subclasses want it
        #value here is the raw extracted from the widget's subform
        #in the form of a dict key:fieldname, value:fieldvalue

        # FIXME: this code is too much plone dependent ....
        #        need to move the default URI-prefix-setting to this package.
        #        (possibly whole create new unique uri to IORDF tool)
        #        other possibility would be to provide overridable factory to
        #        create new named graphs...(doesn't solve uri prefix setting)

        # TODO: should I try to load something here?
        #       or do I just apply data?
        # FIXME: make this here independent of Zope2 !!!!!
        #        maybe override component for Zope2 and do something better here?
        #        also dependency on gu.plone.rdf is bad here (prob. need a Utility here)
        from App.config import getConfiguration
        import uuid

        settings = getConfiguration().product_config.get('gu.plone.rdf', dict())

        contenturi = "%s%s" % (settings.get('baseuri'), uuid.uuid1())

        identifier = URIRef(contenturi)
        obj = Graph(identifier=identifier)

        # for prop, data in value.predicate_objects(value.identifier):
        #     obj.add((identifier, prop, data))

        # for key, data in value.items():
        #     # TODO: can data be a list?
        #     if data is not None:
        #         obj.add((identifier, URIRef(key), data))

        # name = getIfName(self.field.schema)
        # creator = zope.component.queryMultiAdapter(
        #     (self.widget.context, self.widget.request,
        #      self.widget.form, self.widget),
        #     interfaces.IObjectFactory,
        #     name=name)
        # if creator:
        #     obj = creator(value)
        # else:
        #     raise ValueError("No IObjectFactory adapter registered for %s" %
        #                      name)
        return obj

    def toFieldValue(self, value):
        """field value is an Object type, that provides field.schema"""
        if value is NO_VALUE:
            return self.field.missing_value

        if self.widget.subform is None:
            #creepy situation when the widget is hanging in nowhere
            obj = self.createObject(value)
        else:
            if self.widget.subform.ignoreContext:
                obj = self.createObject(value)
            else:
                dm = zope.component.getMultiAdapter(
                    (self.widget.context, self.field), IDataManager)
                try:
                    obj = dm.get()
                except KeyError:
                    obj = self.createObject(value)
                except AttributeError:
                    obj = self.createObject(value)

        if obj is None or obj == self.field.missing_value:
            #if still None create one, otherwise following will burp
            obj = self.createObject(value)

        names = []
        # TODO: find another way to solve property removal:
        #       maybe it's possible to go through serf.widget.subform.fields to get fieldnames this subform operates on
        #       -> how to remove a subgraph completely? there is always the latest changeset included therefore
        #          the graph will never be empty and the object will always hold a reference to the subgraph (problem or not?)
        #
        #       Currently:
        #       -> any additional data in the current (obj) Graph will be removed and the Graph
        #          will be repopulated with data given in value. (otherwise removal of objects won't work)


        #generate value graph from value dict:
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

        # TODO: see also GraphDataManager
        # 1. remove changed props from obj (even those that don't exist in value)
        for prop in set(obj.predicates(obj.identifier, None)):
            if obj.objects(obj.identifier, prop) != value.objects(value.identifier, prop):
                # property has been changed ... remove it
                names.append(prop)
                obj.remove((obj.identifier, prop, None))
        # 2. update possible changes and add new props from value
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

# FIXME: use extensible form here?
from plone.z3cform.fieldsets.extensible import ExtensibleForm
from z3c.form.object import ObjectSubForm
class RDFObjectSubForm(ObjectSubForm):

    def setupFields(self):
        #self.__parent__.field.schema
        context = self.getContent()
        lens = self.__parent__.field.lens
        if lens is not None:
            _, fields = getFieldsFromFresnelLens(lens, context,
                                                 context.identifier)
            self.fields = Fields(*fields)
        else:
            self.fields = Fields()

    def getContent(self):
        # TODO: do I use self.context or parent.value here?
        val = self.__parent__._value
        if val == NO_VALUE:
            return Graph()
        if not isinstance(val, _Graph):
            return Graph()
        return val

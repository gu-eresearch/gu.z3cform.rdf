from rdflib import Graph, URIRef
from zope.schema.interfaces import IField, ICollection
from zope.component import adapts, getUtility
from z3c.form.interfaces import NO_VALUE
from z3c.form.datamanager import DataManager
from gu.z3cform.rdf.interfaces import IORDF, IRDFObjectField, IGraph, IRDFField
from gu.repository.content.interfaces import IRepositoryMetadata
from plone.uuid.interfaces import IUUIDAware


class GraphDataManager(DataManager):
    """
    A data manager that operates on a Graph.
    """
    # FIXME: need to distinguish two different cases here.
    #        1. reference to separate object, which sholud not be removed
    #        2. reference to object that belongs to this one, which sholud be removed.
    #        Possible fix: use relation objects to relate to "external" objects
    # FIXME: currently this impl. leaves "private" sub graphs untouched, in case of multi-subobject it
    #        will even generate new subgraphs and the old ones will be left in database

    adapts(IGraph, IRDFField)

    def __init__(self, context, field):
        self.graph = context
        # FIXME: here we assume, the ordf storage model, that the Graph URI is the same as the individual URI
        self.subj = self.graph.identifier
        self.field = field
        # TODO: think ... this is slightly different to z3c.form fields, where field.__name__ is being used.
        #       __name__ might be useful in case of ORM.. .(but would I then use an N3Field or this datamanager at all?)
        if not hasattr(field, 'prop'):
            import ipdb; ipdb.set_trace()
            # TODO: shall we use field.__name__ with a default url-prefix?
            self.prop = URIRef('http://fixeme.com/noprop')
        else:
            self.prop = field.prop

    def get(self):
        """Get the value.

        If no value can be found, raise an error

        # FIXME: should return a set here, because RDF is unordered. however the widget lookup and ui deals a lot better with lists (except for comparing unordered lists).
        """
        value = list(self.graph.objects(self.subj, self.prop))
        if value is None:
            raise AttributeError
        # TODO: what if field is defined as single, but there are multiple values?
        #       showing one would hide the others, showing all would confuse the field
        # TODO: this code can't deal with sub ojects referenced via BNodes
        # DEL: if len(value) > 1 or ICollection.providedBy(self.field):
        if ICollection.providedBy(self.field):
            # check value_type .. if object, we'll retrieve a graph
            if IRDFObjectField.providedBy(self.field.value_type):
                # load ass subgraphs
                # TODO: do I need to filter out empty graphs?
                handler = getUtility(IORDF).getHandler()
                # TODO: 3 possibilities here... we find it in current graph or in separate or we have to run a query
                # Assume separate Graph here
                value = [handler.get(v) for v in value]
            return value
        if len(value) == 1:
            # return only one value, the field doesn't support more anyway
            value = value[0]
            if IRDFObjectField.providedBy(self.field):
                handler = getUtility(IORDF).getHandler()
                value = handler.get(value)
            return value
        # TODO: check shoulde probably fail here or never reach?
        return None

    def query(self, default=NO_VALUE):
        """Get the value.

        If no value can be found, return the default value.
        If access is forbidden, raise an error.
        """
        try:
            return self.get()
        except AttributeError:
            return default

    def set(self, value):
        """Set the value"""
        # TODO: do we have to remove the referenced graphs as well? (in case of IRDFObjectField)
        handler = getUtility(IORDF).getHandler()
        self.graph.remove((self.subj, self.prop, None))
        if value is None:
            return
        # TODO: can we do IObject for sub-forms to deal with BNodes?
        if not ICollection.providedBy(self.field):
            value = [value]
        for val in value:
            if val is not None:
                # FIXME: check conversion of value to URIRef or Literal?
                handler = getUtility(IORDF).getHandler()
                if isinstance(val, Graph):
                    # a multivalue object field might send in a whole graph
                    self.graph.add((self.subj, self.prop, val.identifier))
                    # TODO: check why this is not managed by ContextGraphDataManagerForObjectFields
                    handler.put(val)
                else:
                    self.graph.add((self.subj, self.prop, val))
        handler.put(self.graph)

    def canAccess(self):
        """Can the value be accessed."""
        return True

    def canWrite(self):
        """Can the data manager write a value."""
        return True


class ContextGraphDataManager(GraphDataManager):
    """
    A data manager that looks up a Graph for a given context and operates on that Graph.
    """

    adapts(IUUIDAware, IRDFField)

    def __init__(self, context, field):
        self.graph = IRepositoryMetadata(context)
        # FIXME: here we assume, the ordf storage model, that the Graph URI is the same as the individual URI
        self.subj = self.graph.identifier
        self.field = field
        # TODO: think ... this is slightly different to z3c.form fields, where field.__name__ is being used.
        #       __name__ might be useful in case of ORM.. .(but would I then use an N3Field or this datamanager at all?)
        if not hasattr(field, 'prop'):
            import ipdb; ipdb.set_trace()
            # TODO: shall we use field.__name__ with a default url-prefix?
            self.prop = URIRef('http://fixeme.com/noprop')
        else:
            self.prop = field.prop

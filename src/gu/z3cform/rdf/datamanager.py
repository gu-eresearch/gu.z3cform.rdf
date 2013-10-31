from rdflib import Graph, URIRef, ConjunctiveGraph
from zope.schema.interfaces import ICollection
from zope.component import adapts, getUtility
from z3c.form.interfaces import NO_VALUE
from z3c.form.datamanager import DataManager
from gu.z3cform.rdf.interfaces import (IORDF, IRDFObjectPropertyField,
                                       IGraph, IRDFField)
from plone.uuid.interfaces import IUUIDAware


class GraphDataManager(DataManager):
    """
    A data manager that operates on a Graph.
    """
    # FIXME: need to distinguish two different cases here.
    #        1. reference to separate object, which sholud not be removed
    #        2. reference to object that belongs to this one, which
    #           sholud be removed.  Possible fix: use relation objects to
    #           relate to "external" objects

    # FIXME: currently this impl. leaves "private" sub graphs
    #        untouched, in case of multi-subobject it will even
    #        generate new subgraphs and the old ones will be left in
    #        database

    adapts(IGraph, IRDFField)

    def __init__(self, context, field):
        self.graph = context
        # FIXME: here we assume, the ordf storage model, that the
        # Graph URI is the same as the individual URI
        self.subj = self.graph.identifier
        self.field = field
        # TODO: think ... this is slightly different to z3c.form
        #       fields, where field.__name__ is being used.  __name__
        #       might be useful in case of ORM.. .(but would I then
        #       use an N3Field or this datamanager at all?)
        if not hasattr(field, 'prop'):
            import ipdb; ipdb.set_trace()
            # TODO: shall we use field.__name__ with a default url-prefix?
            self.prop = URIRef('http://fixme.com/noprop')
        else:
            self.prop = field.prop

    def get(self):
        """Get the value.

        If no value can be found, raise an error

        # FIXME: should return a set here, because RDF is
        # unordered. however the widget lookup and ui deals a lot
        # better with lists (except for comparing unordered lists).
        """
        value = list(self.graph.objects(self.subj, self.prop))
        if value is None:
            raise AttributeError
        # TODO: what if field is defined as single, but there are
        #       multiple values?  showing one would hide the others,
        #       showing all would confuse the field
        if ICollection.providedBy(self.field):
            return value
        if len(value) == 1:
            # return only one value, the field doesn't support more anyway
            return value[0]
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
        # TODO: do we have to remove the referenced graphs as well?
        #       (in case of IRDFObjectPropertyField)
        #    what about: This seems to be only a problem with multi object widgets.
        #       if there is one prop pointing to a sub object I am adding / removing here?
        #       which prop do I have to update if I remove all?
        #    If I keep track of graphs and remove one, I'll have to make sure I remove
        #       all other props pointing to it as well
        handler = getUtility(IORDF).getHandler()
        olddata = list(self.graph.objects(self.subj, self.prop))
        self.graph.remove((self.subj, self.prop, None))
        # if value is None:
        #     handler.put(self.graph)
        #     return
        # TODO: can we do IObject for sub-forms to deal with BNodes?
        if not ICollection.providedBy(self.field):
            value = [value]
        if value is not None:
            for val in value:
                if val is not None:
                    if val in olddata:
                        olddata.remove(val)
                    self.graph.add((self.subj, self.prop, val))
        # clean up orphaned graphs in case we dealt with a multivalue object widget
        if IRDFObjectPropertyField.providedBy(self.field):
            for identifier in olddata:
                # FIXME: here are multiple use cases (1 is supported)
                #   1. current graph has multiple properties that refer to removed graph
                #   2. there are other graphs in the store that might refer to the removed graph
                #   3. I assume there are more
                # TODO: do this only for objectporperties
                self.graph.remove((self.subj, None, identifier))
                handler.remove(identifier)
        # persist current graph
        handler.put(self.graph)

    def canAccess(self):
        """Can the value be accessed."""
        return True

    def canWrite(self):
        """Can the data manager write a value."""
        return True


class ContextGraphDataManager(GraphDataManager):
    """
    A data manager that looks up a Graph for a given context and
    operates on that Graph.
    """

    adapts(IUUIDAware, IRDFField)

    def __init__(self, context, field):
        self.graph = IGraph(context)
        # FIXME: here we assume, the ordf storage model, that the
        # Graph URI is the same as the individual URI
        self.subj = self.graph.identifier
        self.field = field
        # TODO: think ... this is slightly different to z3c.form
        #       fields, where field.__name__ is being used.  __name__
        #       might be useful in case of ORM.. .(but would I then
        #       use an N3Field or this datamanager at all?)
        if not hasattr(field, 'prop'):
            import ipdb; ipdb.set_trace()
            # TODO: shall we use field.__name__ with a default url-prefix?
            self.prop = URIRef('http://fixeme.com/noprop')
        else:
            self.prop = field.prop

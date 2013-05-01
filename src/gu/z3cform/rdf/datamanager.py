from rdflib import Graph, URIRef
from zope.schema.interfaces import IField, ICollection
from zope.component import adapts, getUtility
from z3c.form.interfaces import NO_VALUE
from z3c.form.datamanager import DataManager
from gu.z3cform.rdf.interfaces import IORDF, IRDFObjectField, IGraph, IRDFField
from gu.repository.content.interfaces import IRepositoryMetadata
from plone.uuid.interfaces import IUUIDAware


class GraphDataManager(DataManager):
    # FIXME... for now this works if the context is a graph, but it won't allow us to mix stuff'
    # for now this is ok, and maybe we can mix stuff with subforms :)

    adapts(IUUIDAware, IRDFField)

    def __init__(self, context, field):
        # if (not isinstance(data, Graph)):
        #     raise ValueError("Date must be a rdflib Graph instance: %s" % type(data))
        if not isinstance(context, Graph):
            # TODO: get graph from somewhere
            self.graph = IRepositoryMetadata(context)
        else:
            import ipdb; ipdb.set_trace()
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
        if len(value) > 1 or ICollection.providedBy(self.field):
            # TODO: check if this is a generator or a full list
            return value
        if len(value) == 1:
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
        self.graph.remove((self.subj, self.prop, None))
        if value is None:
            return
        # TODO: can we do IObject for sub-forms to deal with BNodes?
        if not ICollection.providedBy(self.field):
            value = [value]
        for val in value:
            if val is not None:
                # FIXME: check conversion of value to URIRef or Literal?
                self.graph.add((self.subj, self.prop, val))

    def canAccess(self):
        """Can the value be accessed."""
        return True

    def canWrite(self):
        """Can the data manager write a value."""
        return True


class GraphDataManagerForObjectFields(GraphDataManager):

    adapts(IUUIDAware, IRDFObjectField)
    
    def get(self):
        """Get the value.

        returns a single Graph or a list of Graphs

        If no value can be found, raise an error

        # FIXME: should return a set here, because RDF is unordered. however the widget lookup and ui deals a lot better with lists (except for comparing unordered lists).
        """
        value = list(self.graph.objects(self.subj, self.prop))
        if value is None:
            raise AttributeError
        # TODO: what if field is defined as single, but there are multiple values?
        #       showing one would hide the others, showing all would confuse the field
        # TODO: can we do IObject for sub-forms to deal with BNodes?
        # Assume they are al URIRefs, otherwise we have a data problem anyway.
        for idx in range(0, len(value)):
            uri = value[idx]
            # TODO: 3 possibilities here... we find it in current graph or in separate or we have to run a query
            # Assume separate Graph here
            handler = getUtility(IORDF).getHandler()
            value[idx] = handler.get(uri)
        if len(value) > 1 or ICollection.providedBy(self.field):
            # TODO: check if this is a generator or a full list
            return value
        if len(value) == 1:
            return value[0]
        # TODO: check should probably fail here or never reach?
        return None


    def set(self, value):
        """Set the value"""
        # TODO: do we have to remove the referenced graphs as well?
        self.graph.remove((self.subj, self.prop, None))
        if value is None:
            return
        # TODO: can we do IObject for sub-forms to deal with BNodes?
        if not ICollection.providedBy(self.field):
            value = [value]
        handler = getUtility(IORDF).getHandler()
        for val in value:
            if val is not None:
                # FIXME: check conversion of value to URIRef or Literal?
                self.graph.add((self.subj, self.prop, val.identifier))
                handler.put(val)


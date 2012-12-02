from rdflib import Graph, URIRef
from zope.schema.interfaces import IField, ICollection
from zope.component import adapts
from z3c.form.interfaces import NO_VALUE
from z3c.form.datamanager import DataManager


class GraphDataManager(DataManager):
    # FIXME... for now this works if the context is a graph, but it won't allow us to mix stuff'
    # for now this is ok, and maybe we can mix stuff with subforms :)

    adapts(Graph, IField)

    def __init__(self, context, field):
        # if (not isinstance(data, Graph)):
        #     raise ValueError("Date must be a rdflib Graph instance: %s" % type(data))
        if not isinstance(context, Graph):
            # TODO: get graph from somewhere
            pass
        else:
            self.graph = context
            # FIXME: here we assume, the ordf storage model, that the Graph URI is the same as the individual URI
            self.subj = context.identifier
        self.field = field
        # TODO: think ... this is slightly different to z3c.form fields, where field.__name__ is being used.
        #       __name__ might be useful in case of ORM.. .(but would I then use an N3Field or this datamanager at all?)
        if not hasattr(field, 'prop'):
            self.prop = URIRef('http://fixeme.com/noprop')
        else:
            self.prop = field.prop

    def get(self):
        """Get the value.

        If no value can be found, raise an error
        """
        value = list(self.graph.objects(self.subj, self.prop))
        if value is None:
            raise AttributeError
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

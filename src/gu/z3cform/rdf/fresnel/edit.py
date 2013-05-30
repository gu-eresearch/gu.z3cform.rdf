import logging

from gu.z3cform.rdf.interfaces import IIndividual
from gu.z3cform.rdf.interfaces import IORDF
from ordf.namespace import FRESNEL
from rdflib import Namespace, XSD, Literal
from z3c.form import field
from zope.component import getUtility
from zope.dottedname.resolve import resolve
from gu.z3cform.rdf.fresnel.fresnel import Lens, PropertyGroup, ID_CHAR_MAP
from gu.repository.content.interfaces import IRepositoryMetadata

LOG = logging.getLogger(__name__)
Z3C = Namespace(u"http://namespaces.zope.org/z3c/form#")


def getLens(individual):
    lens = None
    formatgraph = getUtility(IORDF).getFresnel()
    for rtype in individual.type:
        if rtype in formatgraph.classLenses:
            lens = formatgraph.classLenses[rtype]
            break
    if lens is not None:
        return lens[0]
    if lens is None:
        # search for a lens with no classDomain:
        for lensuri, lensgraph in formatgraph.lenses.items():
            if lensgraph.value(lensuri, FRESNEL['classLensDomain']) is None:
                return lensgraph
    # FIXME: make sure to select proper lens based on group, priority,
    #        whatever
    return None


def getFieldsFromFresnelLens(lens, graph, resource):
    """

    return a tuple of groups and a list of fields
    """
    fields = []
    groups = []
    for prop, sublens, format in lens.properties(graph, resource,
                                                 sorted=True):
        LOG.info("check for field %s", prop)
        if sublens is not None:
            if isinstance(sublens, PropertyGroup):
                _, subfields = getFieldsFromFresnelLens(sublens, graph,
                                                        resource)

                g = RDFGroupFactory(str(sublens.identifier).translate(ID_CHAR_MAP),
                                    field.Fields(*subfields),
                                    sublens.label(sublens.identifier), None)
                groups.append(g)

            elif isinstance(sublens, Lens):
                # we render a sub object....
                #  retrieve graph this prop is pointing to and build form
                fieldfactory = resolve("gu.z3cform.rdf.schema.RDFObjectField")
                label = format.label(prop)
                fieldkw = {
                    'title': unicode(label),
                    '__name__': str(prop).translate(ID_CHAR_MAP),
                    'classuri': sublens.value(sublens.identifier,
                                              FRESNEL['classLensDomain']),
                    'required': False}
                fieldinst = fieldfactory(prop=prop, **fieldkw)
                # TODO: think about additional paremeters clasuri and lens. both are needed here on the field
                #       but are rather unusual. (maybe as optional parameters into the field constructor?)
                fieldinst.lens = sublens  # necessary to generate fields for subform

                #multi = format.value(format.identifier, Z3C['multi'], default=Literal("false", datatype=XSD.boolean))
                # FIXME: there is a problem with current rdflib zodb and typed literals
                multi = format.value(format.identifier, Z3C['multi'], default=Literal("false"))
                if multi in ('true', '1', 'True'):
                    # multivalued object field requested
                    fieldkw['value_type'] = fieldinst
                    del fieldkw['classuri']
                    fieldfactory = resolve("gu.z3cform.rdf.schema.RDFMultiValueField")
                    fieldinst = fieldfactory(prop=prop, **fieldkw)
                
                if fieldinst is not None:
                    fields.append(fieldinst)
        else:
            if format is None:
                LOG.info("Ignoring field %s . No format", prop)
                continue
            else:
                # it's a simple field create it
                fieldinst = format.getField(prop)
                if fieldinst is not None:
                    fields.append(fieldinst)
    return tuple(groups), fields


# FIXME: turn sublenses into subforms? (multisubforms? ... the only way to
#        handle anon-nodes properly, which still might make troubles when
#        matching data ... e.g.: leave unrecognised fields untouched)
#        however ... need some consistent handling for BNodes ... e.g. display
#        only?
# FIXME: create view / edit / create / browse forms for data not attached to
#        content.
class FieldsFromLensMixin(object):
    """
    assumes, that getContent returns a RDF Graph instance.
    """

    def updateFields(self):
        # TODO: do I have to call super here?
        try:
            # call our superclass updateFields if there is any
            super(FieldsFromLensMixin, self).updateFields()
        except AttributeError:
            pass

        graph = IRepositoryMetadata(self.context)
        individual = IIndividual(graph)
        lens = getLens(individual)
        LOG.info('individual types: %s', individual.type)
        LOG.info('picked lens: %s', lens)
        fields = []
        groups = ()
        if lens is not None:
            groups, fields = getFieldsFromFresnelLens(lens, individual.graph,
                                                      individual.identifier)

        if hasattr(self, 'groups'):
            if (self.groups or groups) and fields:
                # turn main fields into Group only if we have fields to add to and if this form
                # already has groups
                g = RDFGroupFactory('Default_RDF_Lens', field.Fields(*fields),
                                    'RDF Metadata', None)
                fields = ()
                groups = (g, ) + groups
            self.groups += groups

        # if there is still something in fields we add it to the normal field list
        if self.fields is not None:
            self.fields += field.Fields(*fields)
        else:
            self.fields = field.Fields(*fields)
            
        # apply widgetFactories here
        for g in (self, ) + tuple(self.groups):
            for f in g.fields.values():
                if hasattr(f.field, 'widgetFactory'):
                    LOG.info('apply costum widgetFactory %s to for field %s', str(f.field.widgetFactory), f.field.__name__)
                    if isinstance(f.field.widgetFactory, dict):
                        for key, value in f.field.widgetFactory.items():
                            f.widgetFactory[key] = value
                    else:
                        f.widgetFactory = f.field.widgetFactory
        
    def applyChanges(self, data):
        # TODO: move this out to edit view, so that this class can be safely
        #       re-used in display forms
        from zope.security.management import getInteraction
        uname = "Anonymous"
        try:
            interaction = getInteraction()
            #import ipdb; ipdb.set_trace()
        except Exception:
            pass
        # # get current username:
        # #  other ways via SecurityManager or plone_context_state view
        # # from AccessControl import getSecurityManager
        # # user = getSecurityManager().getUser()
        # # username = user.getUserName()
        # mt = getToolByName(self, 'portal_membership')
        # # mt.isAnonymousUser() ... can't really happn?
        # uname = mt.getAuthenticatedMember().getUserName()
        # #import pdb; pdb.set_trace() # check for changeset generation der

        #######################################################################
        ## way 1 ... use ordf.handler.context ...  ordf assumes, that graphs are
        ##      rather small, and cover mostly only the data about one
        ##      individual.  this way it is easy to load and compare complete
        ##      graphs. (does currently not fit into our model).
        ## TODO: coed below does not work entirely correct. changecontexts
        ##       retrieve the original themselves and
        ##       assume only updates graphs are being added
        #######################################################################
        # get a change context from the handler
        # TODO: maybe capture reason in form?
        
        ####### TODO remove this stuff here, the transaction handler takes care of changeset generation
        #import ipdb; ipdb.set_trace()
        #rdfhandler = getUtility(IORDF).getHandler()
        #cc = rdfhandler.context(user=uname, reason="edited via web interface")
        #cc.add(IRepositoryMetadata(self.context))
        # make changes
        result = super(FieldsFromLensMixin, self).applyChanges(data)
        # store modified data
        # TODO: check result whether it's worth doing all this
        # TODO: maybe mark graph as dirty (zodb way) and process dirty graphs in transaction handler
        # TODO: do difference processing in transaction and decide there? (possibly expensive)
        graph = IRepositoryMetadata(self.context)
        rdfhandler = getUtility(IORDF).getHandler()
        rdfhandler.put(graph)
        #cc.add(graph)
        # send changeset
        #cc.commit()
        #
        #
        # TODO: instead of commit ... put ChangeSet into Datamanager, which
        #       will commit at end of transaction.
        #       plone specific behaviour => revised: let handler do transaction
        #       handling
        # TODO: probably have to re-update fields, in case rdf:type has changed

        #######################################################################
        ## way 2 ... generate changeset manually and send it to store
        ##
        #######################################################################
        # olddata = Graph(identifier=self.content.identifier)
        # olddata += self.content
        # result = super(EditForm, self).applyChanges(data)
        # cs = ChangeSet(uname, 'edited via web interface')
        # cs.diff(olddata, self.content)  # TODO returns number of changes..
        # cs.commit()  # freeze the changeset and add changeset metadat
        # # send changeset over wire

        return result


#from plone.z3cform.fieldsets import group
from z3c.form import group


class RDFGroup(FieldsFromLensMixin, group.Group):

    def getLens(self, individual):
        if self.lens is not None:
            return self.lens
        return getLens(individual)

    def getContent(self):
        # TODO: make this more versatile.
        #       currently the context is supplied by parent form
        #return self.__parent__.getContentGraph()
        return self.__parent__.getContent()


from zope.interface import implements
from plone.z3cform.fieldsets.interfaces import IGroupFactory


class RDFGroupFactory(object):
    implements(IGroupFactory)

    def __init__(self, __name__, fields, label=None, description=None):
        self.__name__ = __name__
        self.fields = fields

        self.label = label or __name__
        self.description = description

    def __call__(self, context, request, parentForm):
        g = RDFGroup(context, request, parentForm)
        g.__name__ = self.__name__
        g.label = self.label
        g.description = self.description
        g.fields = self.fields
        return g

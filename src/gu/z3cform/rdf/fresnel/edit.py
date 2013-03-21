import logging

from gu.z3cform.rdf.interfaces import IIndividual
from gu.z3cform.rdf.interfaces import IORDF
from ordf.namespace import FRESNEL
from rdflib import Namespace
from z3c.form import field
from zope.component import getUtility
from zope.dottedname.resolve import resolve
from gu.z3cform.rdf.fresnel.fresnel import Lens, PropertyGroup

LOG = logging.getLogger(__name__)
Z3C = Namespace(u"http://namespaces.zope.org/z3c/form#")


def getLens(individual):
    lens = None
    formatgraph = getUtility(IORDF).getFresnel()
    for rtype in individual.type:
        if rtype in formatgraph.classLenses:
            lens = formatgraph.classLenses[rtype]
            break
    if lens is None:
        # search for a lens with no classDomain:
        for lensuri, lensgraph in formatgraph.lenses.items():
            if lensgraph.value(lensuri, FRESNEL['classLensDomain']) is None:
                lens = [lensgraph]
                break
    # FIXME: make sure to select proper lens based on group, priority,
    #        whatever
    return lens[0]


def getFieldsFromFresnelLens(lens, graph, resource):
    fields = []
    groups = []
    for prop, sublens, format in lens.properties(graph, resource,
                                                 sorted=True):
        LOG.info("check for field %s", prop)
        if sublens is not None:
            if isinstance(sublens, PropertyGroup):
                _, subfields = getFieldsFromFresnelLens(sublens, graph,
                                                        resource)

                g = RDFGroupFactory(str(sublens.identifier).replace('-', '_'),
                                    field.Fields(*subfields),
                                    sublens.label(sublens.identifier), None)
                groups.append(g)

            elif isinstance(sublens, Lens):
                # we render a sub object....
                #  retrieve graph this prop is pointing to and build form
                # import ipdb; ipdb.set_trace()
                fieldfactory = resolve("gu.z3cform.rdf.schema.RDFObjectField")
                label = format.label(prop)
                fieldkw = {
                    'title': unicode(label),
                    '__name__': str(prop).replace('-', '_'),
                    'classuri': sublens.value(sublens.identifier,
                                              FRESNEL['classLensDomain']),
                    'required': False}
                fieldinst = fieldfactory(prop=prop, **fieldkw)
                if fieldinst is not None:
                    fieldinst.lens = sublens  # TODO: make this a parameter to
                                              #       field instance, optional,
                                              #       and classuri as well,
                    fields.append(fieldinst)
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
#        handle anon-nodes properly, which stil might make troubles when
#        matching data ... e.g.: leave unrecognised fields untouched)
#        however ... need some consistent handling for BNodes ... e.g. display
#        only?
# FIXME: create view / edit / create / browse forms for data not attached to
#        content.
class FieldsFromLensMixin(object):
    '''
    assumes, that getContent returns a RDF Graph instance.
    '''

    def updateFields(self):
        # TODO: do I have to call super here?
        #import ipdb; ipdb.set_trace()
        try:
            # call our superclass updateFields if there is any
            super(FieldsFromLensMixin, self).updateFields()
        except AttributeError:
            pass
        individual = IIndividual(self.getContent())
        lens = getLens(individual)
        fields = []
        if lens is not None:
            groups, fields = getFieldsFromFresnelLens(lens, individual.graph,
                                                      individual.identifier)
        if self.fields is not None:
            self.fields += field.Fields(*fields)
        else:
            self.fields = field.Fields(*fields)

        if hasattr(self, 'groups'):
            self.groups += groups
        # TODO: if group list is not empty, remove all fields from main fileds
        #       and add them as new first group. (if not disabled)

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
        ## way 1 ... use ord.handler.context ...  ordf assumes, that graphs are
        ##      rather small, and cover mostly only the data about one
        ##      individual.  this way it is easy to load and compare complete
        ##      graphs. (does currently not fit into our model).
        ## TODO: coed below does not work entirely correct. changecontexts
        ##       retrieve the original themselves and
        ##       assume only updates graphs are being added
        #######################################################################
        # get a change context from the handler
        # TODO: maybe capture reason in form?
        rdfhandler = getUtility(IORDF).getHandler()
        cc = rdfhandler.context(user=uname, reason="edited via web interface")
        # make changes
        result = super(FieldsFromLensMixin, self).applyChanges(data)
        # store modified data
        cc.add(self.getContent())
        # send changeset
        cc.commit()
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
        return self.__parent__.getContentGraph()
        #return self.__parent__.getContent()


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

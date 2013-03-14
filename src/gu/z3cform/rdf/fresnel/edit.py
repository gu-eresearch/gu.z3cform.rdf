from zope.interface import Interface
from z3c.form import field
from zope import schema
from zope.schema.interfaces import ICollection
from gu.z3cform.rdf.interfaces import IIndividual
from gu.z3cform.rdf.interfaces import IORDF
from gu.z3cform.rdf.schema import RDFN3Field, RDFMultiValueField
from zope.dottedname.resolve import resolve


from rdflib import URIRef, RDF, Namespace, OWL
from zope.component import getUtility
# from org.ausnc.rdf.behavior.interfaces import IRDFMetadata
# from org.ausnc.rdf.interfaces import IORDF, IRDFData
# from org.ausnc.rdf.fresnel.field import RDFLiteralField, RDFMultiValueField
# from org.ausnc.rdf.fresnel.field import RDFLiteralLineField, RDFURIRefField
# from org.ausnc.rdf.fresnel.field import RDFN3Field
import logging
#from z3c.form.form import EditFrrm as BaseEditForm
from ordf.graph import Graph
from ordf.vocab.changeset import ChangeSet
from gu.z3cform.rdf.fresnel.fresnel import Fresnel
from ordf.namespace import FRESNEL

#from Products.CMFCore.utils import getToolByName

LOG = logging.getLogger(__name__)

#FORMAT = Namespace(u"http://aperture.semanticdesktop.org/ontology/sourceformat#")
Z3C = Namespace(u"http://namespaces.zope.org/z3c/form#")

# FIXME: turn sublenses into subforms? (multisubforms? ... the only way to handle anon-nodes properly, which stil might make troubles when matching data ... e.g.: leave unrecognised fields untouched)
#   however ... need some consistent handling for BNodes ... e.g. display only?
# FIXME: create view / edit / create / browse forms for data not attached to content.
class FieldsFromLensMixin(object):
    '''
    assumes, that getContent returns a RDF Graph instance.
    '''

    def getLens(self, individual):
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
                    lens = lensgraph
                    break
        # FIXME: make sure to select proper lens based on group, priority, whatever
        return lens[0]

    def _getFieldsFromFresnelLens(self, lens, graph, resource):
        fields = []
        for prop, sublens, format in lens.properties(graph, resource, sorted=True):
            LOG.info("check for field %s", prop)
            if format is None:
                LOG.info("Ignoring field %s . No format", prop)
                continue
            if sublens is not None:
                # we render a sub object....
                #  retrieve graph this prop is pointing to and build form
                # import ipdb; ipdb.set_trace()
                fieldfactory = resolve("gu.z3cform.rdf.schema.RDFObjectField")
                label = format.label(prop)
                fieldkw = {'title': unicode(label),
                           '__name__': str(prop).replace('-', '_'),
                           'classuri': sublens.value(sublens.identifier, FRESNEL['classLensDomain']),
                           'required': False}
                field = fieldfactory(prop=prop, **fieldkw)
                if field is not None:
                    field.lens = sublens  # TODO: make this a parameter to field instance,
                                          #       optional, and classuri as well, 
                    fields.append(field)
            else:
                # it's a simple field create it
                field = format.getField(prop)
                if field is not None:
                    fields.append(field)
        return fields

    # this update is taylored to Plone, not sure whether there should be an update here, or in the target framework
    # def update(self):
    #     rdftool = getUtility(IORDF)
    #     self.formatgraph = rdftool.getFresnelGraph()
    #     self.rdfhandler = rdftool.getHandler()
    #     super(EditForm, self).update()

        
    def updateFields(self):
        # TODO: do I have to call super here?
        individual = IIndividual(self.getContent())
        lens = self.getLens(individual)
        fields = []
        if lens is not None:
            fields = self._getFieldsFromFresnelLens(lens, individual.graph, individual.identifier)
        self.fields = field.Fields(*fields)
        # TODO: apply widgetfactories here?
        # FIXME: this is an ugly hack to pass the widgetFactory through. ... theschema fieldsholud not be bothered with widgets at all
        for z3cfield in self.fields.values():
            if hasattr(z3cfield.field, 'widgetFactory'):
                z3cfield.widgetFactory = z3cfield.field.widgetFactory
        

    def applyChanges(self, data):
        # TODO: move this out to edit view, so that this class can be safely re-used in display forms
        from zope.security.management import getInteraction
        uname = "Anonymous"
        try:
            interaction = getInteraction()
            #import ipdb; ipdb.set_trace()
        except Exception, e:
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
        ## TODO: coed below does not work entirely correct. changecontexts retrieve the original themselves and
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
        # TODO: instead of commit ... put ChangeSet into Datamanager, which will commit at end of transaction.
        #       plone specific behaviour => revised: let handler do transaction handling
        # TODO: probably have to re-update fields, in case rdf:type has changed

        #######################################################################
        ## way 2 ... generate changeset manually and send it to store
        ##      
        #######################################################################
        # olddata = Graph(identifier=self.content.identifier)
        # olddata += self.content
        # result = super(EditForm, self).applyChanges(data)
        # cs = ChangeSet(uname, 'edited via web interface')  
        # cs.diff(olddata, self.content)  # TODO returns number of changes... log it?
        # cs.commit()  # freeze the changeset and add changeset metadat
        # # send changeset over wire

        return result

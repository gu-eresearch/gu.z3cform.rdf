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
from ordf.vocab.fresnel import Fresnel

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

    # def getContent(self):
    #     # TODO: might be nice to implement a RDF-Graph data handler and use graph directly as data source
    #     #       (makes sublenses easier?)
    #     # TODO: on remove fo sub object: when to remove sub object?
    #     #       1. if it's a BNODE it must be removed
    #     #       2. don't remove it
    #     rdfobj = IRDFMetadata(self.context, None)
    #     if rdfobj:
    #         graphuri = IRDFData(rdfobj).graphuri
    #     else:
    #         graphuri = None
    #     if self._content is None:
    #         # use get graph uri adapter?
    #         subject = self.context.subjecturi
    #         if subject:
    #             subject = URIRef(subject)
    #             self._content = self.rdfhandler.get(graphuri)
    #         else:
    #             self._content = Graph(identifier=graphuri)
    #         self._content.contexturi = subject
    #     return self._content

    # content = property(getContent)



    def getLens(self, individual):
        lens = None
        # FIXME: getting the compiled Fresnel graph sholud be done in a better way
        # FIXME: move this into IORDF utility, and also lens discover algorithm
        formatgraph = getUtility(IORDF).getFresnelGraph()
        formatgraph = Fresnel(store=formatgraph.store,
                              identifier=formatgraph.identifier)
        formatgraph.compile()
        for rtype in individual.type:
            if rtype in formatgraph.classLenses:
                lens = formatgraph.classLenses[rtype]
                break
        if lens is None:
            lens = formatgraph.classLenses[OWL['Thing']]
        return lens

    def _getField(self, format, prop, formatid):
        # TODO: pick correct language
        label = format.label(prop)
        fielddef = format.value(formatid, Z3C.field)
        # TODO: the format does not know about the sub object field... :(
        # fieldname = format.value(fielddef, Z3C.fieldName)
        fieldname = format.value(formatid, Z3C.fieldName)
        if fieldname is None:
            # FIXME: this here ignores undefined fields
            LOG.warn("ignoring field %s for %s", prop, self.getContent().identifier)
            return None
        # if there is no fieldName, we could look up rdf:type for property ... (owl:DataTypeProperty, owl;ObjectProperty?, rdfs:Property -> need to check data)
        # TODO: get field type: check rdfs:range for this property

        # TODO: interesting display stuff:
        #       fresnel:value, valueFormat, 

        # build field parameters
        fieldkw = {'title': unicode(label),
                   '__name__': str(prop).replace('-', '_'), #  FIXME: check to use valid python name?
        # have to replace all - in names with underscores. z3c.forms assumes - separate name parts and might convert them to '.' if necessary. if '-' is part of actual name and not separataor, then the name will no longer match after all '-' are replaced by '.'
                   'required': False}  # FIXME: should come from lens

        # TODO: set fieldkw['rdftype'] if defined

        # determine cardinality of property ....
        #    owl:min/max/cardinality
        #    fieldtype?, propertyFormat?
        # for now let fieldtype define it, and use z3c:value_type as in python
        # TODO: support things like, vocabularies, sparql queries, etc...
        fieldfactory = resolve(fieldname)
        if ICollection.implementedBy(fieldfactory):
            # determine value_type
            #value_type = format.value(fielddef, Z3C.valueType)
            value_type = format.value(formatid, Z3C.valueType)
            value_type_factory = resolve(value_type)
            # FIXME: this is a special case .... need to make this more generic; e.g. let IORDF tool handle this
            #        or find another way to create vocabularies or choice fields via rdf.
            classuri = format.value(formatid, Z3C.valueClass)
            subfieldkw = fieldkw.copy()
            del subfieldkw['title']  # remove title from subfield.
            if classuri is not None:
                value_type = value_type_factory(prop=prop,
                                                classuri=classuri,
                                                **subfieldkw)
            else:
                value_type = value_type_factory(prop=prop, **subfieldkw)
            fieldkw.update({'value_type': value_type})
        else:
            # FIXME: same special case as above
            # we might thave a choice field here without a surrounding list
            classuri = format.value(formatid, Z3C.valueClass)
            if classuri is not None:
                fieldkw['classuri'] = classuri
                
        LOG.info("Add field %s for %s", prop, self.getContent().identifier)
        field = fieldfactory(prop=prop,
                             **fieldkw)

        widgetfactory = format.value(formatid, Z3C.widgetFactory)
        if widgetfactory is not None:
            field.widgetFactory = resolve(widgetfactory)


        # field = RDFMultiValueField(__name__=str(prop),
        #                            prop=prop,
        #                            value_type=RDFN3Field(prop=prop, **fieldkw),
        #                            #**fieldkw
        # )
        return field

    def _getFieldsFromFresnelLens(self, lens, graph, resource):
        fields = []
        for prop, sublens, format in lens.properties(graph, resource, sorted=True):
            #LOG.info("%s: %s %s" % (prop, sublens, format))
            # if sublens != None:
            #     import ipdb; ipdb.set_trace()
            # if sublens -> subgroup? / subform / new fieldprefix

            LOG.info("check for field %s", prop)
            field = self._getField(format, prop, format.identifier)
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

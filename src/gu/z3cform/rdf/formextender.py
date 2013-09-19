import logging
from zope.interface import Interface
from zope.component import adapter, getMultiAdapter
from plone.z3cform.fieldsets.extensible import FormExtender
from z3c.form.interfaces import IFormLayer
from gu.z3cform.rdf.interfaces import IIndividual, IGraph, IRDFTypeMapper
from gu.z3cform.rdf.fresnel import getLens
from gu.z3cform.rdf.fresnel import getFieldsFromFresnelLens
from ordf.graph import Graph

LOG = logging.getLogger(__name__)


# context, request, form
@adapter(Interface, IFormLayer, Interface)
class RDFFormExtender(FormExtender):

    def update(self):
        # add form:
        #   self.form.portal_type??? or custom field on form

        # all forms:
        #  create fields
        #  set IRDFMetadata interface on each field
        #  add field to form
        # => in theory the form engine should look up an adapter for IRDFMetadata
        #    to try to set the field values
        # TODO: DataManager needs to do the
        # TODO: AddForm... self.form.portal_type
        #                  self.form.getEmptyGraph !!!!!
        from z3c.form.interfaces import IAddForm
        # FIXME: ... this should be externalised somewhere
        #        or separate formextenders for Add, edit, display
        if IAddForm.providedBy(self.form):
            # the form context is the container ...
            tm = getMultiAdapter((self.context, self.request, self.form), IRDFTypeMapper)
            graph = Graph()
            tm.applyTypes(graph)
        else:
            graph = IGraph(self.context, None)
        if graph is None:
            return
        individual = IIndividual(graph)
        lens = getLens(individual)
        LOG.info('individual types: %s', individual.type)
        LOG.info('picked lens: %s', lens)
        groups = fields = ()
        if lens is not None:
            groups, fields = getFieldsFromFresnelLens(lens, individual.graph,
                                                      individual.identifier)

        # transfer fresnel fields to form:
        for field in fields:
            LOG.info("adding field %s", field.__name__)
            self.add(field)
        for group in groups:
            LOG.info("process group: %s", group.label)
            for field in group.fields.values():
                LOG.info("adding field %s", field.__name__)
                self.add(field)
                self.add(field, group=group.label)

        # processFields(self.form, iface)
        # processFieldMoves(self.form, iface)


def example_extender_code(self):
    """
    self the FormExtender instance
    """
    from gu.z3cform.rdf.schema import RDFLiteralLineField
    from gu.z3cform.rdf.fresnel.fresnel import ID_CHAR_MAP
    from ordf.namespace import DC as DCTERMS
    # add a manual field
    prop = DCTERMS['rights']
    field = RDFLiteralLineField(title=u'RDF Rights',
                                __name__=str(prop).translate(ID_CHAR_MAP),
                                required=False,
                                prop=prop)
    #field.interface = IRDFMetadata
    self.add(field)  # group='grouplabel', index='insertindex'

    # use a supermodel xml to add some more
    from plone.supermodel import loadString
    model = loadString(SCHEMA)
    from plone.autoform.utils import processFields, processFieldMoves
    iface = model.schemata['']
    processFields(self.form, iface)
    processFieldMoves(self.form, iface)
    # move subjects field from different fieldset before default fieldset title
    self.move('IDublinCore.subjects', before='IDublinCore.title')


SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<model xmlns="http://namespaces.plone.org/supermodel/schema"
       xmlns:form="http://namespaces.plone.org/supermodel/form"
       xmlns:security="http://namespaces.plone.org/supermodel/security">
    <schema>
        <field type="gu.z3cform.rdf.schema.RDFLiteralLineField" name="one">
            <title>RDF One</title>
            <description>RDF form help</description>
            <prop>http://my.namespace/test#one</prop>
        </field>
<!-- <field name="dummy" type="zope.schema.TextLine">
  <default>abc</default>
  <description>Test desc</description>
  <max_length>10</max_length>
  <min_length>2</min_length>
  <missing_value>m</missing_value>
  <readonly>True</readonly>
  <required>False</required>
  <title>Test</title>
</field> -->
    <fieldset name="test"
          label="Test Fieldset"
          description="Description of test fieldset">
      <field type="gu.z3cform.rdf.schema.RDFLiteralLineField" name="two">
        <description>RDF two form help</description>
        <title>Rdf Two</title>
        <prop>http://my.namespace/test#two</prop>
      </field>
<!-- type and name are required for field-->
<!--<field type="zope.schema.TextLine"
        name="plone.app.content.dexterity.behaviors.metadat.IDublinCore.title"
       form:after="plone.app.content.dexterity.behaviors.metadat.IDublinCore.description">
        <title>Title override</title>
      </field> -->
    </fieldset>
    </schema>
</model>
"""

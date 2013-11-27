import logging

from gu.z3cform.rdf.interfaces import IIndividual
from gu.z3cform.rdf.interfaces import IORDF
from gu.z3cform.rdf.namespace import Z3C
from ordf.namespace import FRESNEL
from rdflib import Literal, XSD
from z3c.form import field
from zope.component import getUtility
from zope.dottedname.resolve import resolve
from gu.z3cform.rdf.fresnel.fresnel import Lens, PropertyGroup, ID_CHAR_MAP
from plone.z3cform.fieldsets.group import GroupFactory

LOG = logging.getLogger(__name__)


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


def _toFormFields(fields):
    """
    convert schema fields to form fields and apply widgetFactory
    """
    fields = field.Fields(*fields)
    for name in fields:
        if hasattr(fields[name].field, 'widgetFactory'):
            #LOG.info("apply widgetFactory %s to %s", fields[name].field.widgetFactory, name)
            for key, item in fields[name].field.widgetFactory.items():
                fields[name].widgetFactory[key] = item
    return fields


def getFieldsFromFresnelLens(lens, graph, resource):
    """

    return a tuple of groups and a list of fields
    """
    fields = []
    groups = []
    for prop, sublens, format in lens.properties(graph, resource,
                                                 sorted=True):
        #LOG.info("check for field %s", prop)
        if sublens is not None:
            if isinstance(sublens, PropertyGroup):
                _, subfields = getFieldsFromFresnelLens(sublens, graph,
                                                        resource)
                g = GroupFactory(str(sublens.identifier).translate(ID_CHAR_MAP),
                                 subfields,
                                 sublens.label(sublens.identifier), None)
                groups.append(g)

            elif isinstance(sublens, Lens):
                # we render a sub object....
                #  retrieve graph this prop is pointing to and build form
                fieldfactory = resolve("gu.z3cform.rdf.schema.RDFObjectPropertyField")
                label = format.label(prop)
                fieldkw = {
                    'title': unicode(label),
                    '__name__': str(prop).translate(ID_CHAR_MAP),
                    'required': False}
                fieldinst = fieldfactory(prop=prop, **fieldkw)
                # TODO: think about additional paremeters clasuri and lens. both are needed here on the field
                #       but are rather unusual. (maybe as optional parameters into the field constructor?)
                fieldinst.lens = sublens  # necessary to generate fields for subform

                #multi = format.value(format.identifier, Z3C['multi'], default=Literal("false", datatype=XSD.boolean))
                # FIXME: there is a problem with current rdflib zodb and typed literals
                multi = format.value(format.identifier, Z3C['multi'], default=Literal("false", datatype=XSD['boolean']))
                if multi.toPython() in ('true', '1', 'True', True):
                    # multivalued object field requested
                    fieldkw['value_type'] = fieldinst
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
    return tuple(groups), _toFormFields(fields)

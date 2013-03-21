#
# Fresnel implementation to support z3c fresnel extensions.
import string
from ordf.graph import Graph
from ordf.collection import Collection
from ordf.namespace import FRESNEL, RDF
from rdflib import Namespace, BNode
from gu.z3cform.rdf.vocabulary import SparqlInstanceVocabularyFactory
from gu.z3cform.rdf.vocabulary import SparqlVocabularyFactory

Z3C = Namespace(u'http://namespaces.zope.org/z3c/form#')

# TODO: this is used toconvert URLs to valid html-id's. maybe use proper
#        url namespace prefix and replace only tho colon with _
ID_CHAR_MAP = string.maketrans(':/-#.', '_____')


class Fresnel(Graph):
    """
    .. automethod:: format
    """
    __types__ = []

    def __init__(self, *av, **kw):
        super(Fresnel, self).__init__(*av, **kw)
        self.lenses = {}
        self.classLenses = {}  # there might be more than one here for the same
                               # class
        self.instanceLenses = {}  # similar here
        self.groups = {}
        self._compiled = False
        self.fields = {}
        self.vocabularies = {}
        self.propertyGroups = {}

    def getGroup(self, identifier, create=True):
        group = self.groups.get(identifier)
        if group is None and create:
            group = Group(identifier=identifier)
            group += self.bnc((identifier, None, None))
            self.groups[identifier] = group
        return group

    def addClassLens(self, clsuri, lens):
        if clsuri not in self.classLenses:
            self.classLenses[clsuri] = []
        self.classLenses[clsuri].append(lens)

    def addInstanceLens(self, insturi, lens):
        if insturi not in self.instanceLenses:
            self.instanceLenses[insturi] = []
        self.instanceLenses[insturi].append(lens)

    def compile(self):
        if self._compiled:
            return
        self._compiled = True

        for g in self.distinct_subjects(RDF['type'], FRESNEL['Group']):
            self.getGroup(g)

        for f in self.distinct_subjects(RDF['type'], Z3C['Field']):
            field = Field(self, identifier=f)
            field += self.bnc((f, None, None))
            self.fields[f] = field

        for g in self.distinct_subjects(RDF['type'], Z3C['PropertyGroup']):
            propgroup = PropertyGroup(fresnel=self, identifier=g)
            propgroup += self.bnc((g, None, None))
            self.propertyGroups[g] = propgroup
            for grp in propgroup.objects(g, FRESNEL["group"]):
                group = self.getGroup(grp)
                #group.lenses[l] = lens
                propgroup.addGroup(group)

        for v in self.distinct_subjects(RDF['type'], Z3C['Vocabulary']):
            vocab = Vocabulary(identifier=v)
            vocab += self.bnc((v, None, None))
            self.vocabularies[v] = vocab

        for fmt in self.distinct_subjects(RDF["type"], FRESNEL["Format"]):
            format = Format(identifier=fmt)
            format += self.bnc((fmt, None, None))
            for grp in format.objects(fmt, FRESNEL["group"]):
                group = self.getGroup(grp)
                for dom in format.objects(fmt,
                                          FRESNEL["propertyFormatDomain"]):
                    group.addFormat(dom, format)
                format.addGroup(group)
                fld = format.value(fmt, Z3C['field'])
                format.field = self.fields[fld]

        for l in self.distinct_subjects(RDF["type"], FRESNEL["Lens"]):
            lens = Lens(fresnel=self, identifier=l)
            lens += self.bnc((l, None, None))
            self.lenses[l] = lens

            for cls in lens.objects(l, FRESNEL["classLensDomain"]):
                self.addClassLens(cls, lens)
            for inst in lens.objects(l, FRESNEL["instanceLensDomain"]):
                self.addInstanceLense(inst, lens)
            for grp in lens.objects(l, FRESNEL["group"]):
                group = self.getGroup(grp)
                group.lenses[l] = lens
                lens.addGroup(group)


class Group(Graph):

    lenses = None  # dict
    formats = None

    def __init__(self, *av, **kw):
        super(Group, self).__init__(*av, **kw)
        self.lenses = {}
        self.formats = {}

    def addFormat(self, dom, format):
        # dom ... fresnel:propertyFormatDomain
        if dom not in self.formats:
            self.formats[dom] = []
        self.formats[dom].append(format)


class Format(Graph):

    groups = None

    def __init__(self, *av, **kw):
        super(Format, self).__init__(*av, **kw)
        self.groups = []
        self.field = None
        self._fields = {}

    def addGroup(self, group):
        # group .. Group instance
        if group not in self.groups:
            self.groups.append(group)

    def label(self, property):
        # what spaghetti is this!
        # TODO: clean and simplify this code
        for _s, _p, label in self.triples((self.identifier, FRESNEL["label"],
                                           None)):
            if label == FRESNEL["none"]:
                return None
            else:
                return label
        try:
            qname = self.namespace_manager.qname(property)
            if not qname.startswith("_"):
                return qname
        except:
            pass
        label = ":" + property.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        return label

    def getField(self, property):
        if property not in self._fields:
            field = self.field.getField(property, self.label(property))
            widgetFactory = self.value(self.identifier, Z3C['widgetFactory'])
            if widgetFactory is not None:
                field.widgetFactory = resolve(widgetFactory)
            self._fields[property] = field
        return self._fields[property]


class Lens(Graph):

    groups = None
    fresnel = None

    def __init__(self, fresnel, identifier):
        super(Lens, self).__init__(identifier=identifier)
        self.fresnel = fresnel
        self.groups = []

    def addGroup(self, group):
        # group .. Group instance
        if group not in self.groups:
            self.groups.append(group)

    def getFormat(self, prop):
        # check groups in order
        for group in self.groups:
            if prop in group.formats:
                # FIXME: which one in the list is the best format?
                return group.formats[prop][0]
        # TODO: is there some sort of default format?
        return None

    def properties(self, graph, resource, sorted=False):
        # * sorted is applied to list generated by fresnel:allProperties
        properties = []
        for properties in self.objects(self.identifier,
                                       FRESNEL["showProperties"]):
            properties = Collection(self, properties)
            properties = list(properties)
            break
        hideProperties = []
        for hideProperties in self.objects(self.identifier,
                                           FRESNEL["hideProperties"]):
            hideProperties = Collection(self, hideProperties)
            hideProperties = list(hideProperties)
            break
        subProperties = []
        for prop in properties:
            if isinstance(prop, BNode):
                if self.one((prop, RDF["type"],
                             FRESNEL["PropertyDescription"])):
                    x = self.one((prop, FRESNEL["sublens"], None))
                    if x:
                        lens = self.fresnel.lenses.get(x[2])
                    else:
                        lens = None
                        for prop in self.objects(prop, FRESNEL["property"]):
                            if prop not in hideProperties:
                                yield prop, lens, self.getFormat(prop)
                                subProperties.append(prop)
                elif self.one((prop, RDF["type"], Z3C["PropertyGroup"])):
                    x = self.one((prop, Z3C["propertyGroup"], None))
                    if x:
                        group = self.fresnel.propertyGroups.get(x[2])
                        yield None, group, None
                    # this here is not about a single property. if there is a
                    # lens, return otherwise continue
            elif prop == FRESNEL["allProperties"]:
                proplist = graph.distinct_predicates(resource, None)
                if sorted:
                    proplist.sort()
                for prop in proplist:
                    if (prop not in hideProperties and
                        prop not in subProperties and
                        prop not in properties):
                        yield prop, None, self.getFormat(prop)
            else:
                if prop not in hideProperties:
                    yield prop, None, self.getFormat(prop)


class PropertyGroup(Lens):

    pass


from zope.dottedname.resolve import resolve
from zope.schema.interfaces import ICollection


class Field(Graph):

    def __init__(self, fresnel, identifier):
        super(Field, self).__init__(identifier=identifier)
        self.fresnel = fresnel

    def initField(self, prop, fieldkw):
        field = None
        # TODO: possibly do some error checking here; at least to generate
        #       meaningful errors
        fieldClass = resolve(self.value(self.identifier, Z3C['fieldName']))
        if ICollection.implementedBy(fieldClass):
            # it's a multi valued field, let's check sub field type
            valueType = resolve(self.value(self.identifier, Z3C['valueType']))
            # TODO: possibly support list / collection of classes,
            vocabulary = self.value(self.identifier, Z3C['vocabulary'])
            subfieldkw = fieldkw.copy()
            del subfieldkw['title']
            if vocabulary is not None:
                # a query based vocabulary?
                subfieldkw['vocabulary'] = \
                    self.fresnel.vocabularies[vocabulary]()
            # None of the above ... e.g. simple text field?
            fieldkw['value_type'] = valueType(prop=prop,
                                              **subfieldkw)
        else:
            # might be a single select vocabulary driven field:
            vocabulary = self.value(self.identifier, Z3C['vocabulary'])
            if vocabulary is not None:
                # a query based vocabulary?
                fieldkw['vocabulary'] = self.fresnel.vocabularies[vocabulary]()
        field = fieldClass(prop=prop, **fieldkw)

        return field

    def getField(self, prop, label, required=False):
        # this returns a schema field. not a z3c.form.field.Field
        fieldkw = {'title': unicode(label),
                   '__name__': str(prop).translate(ID_CHAR_MAP),
                   # FIXME: check to use valid python name?
                   # have to replace all - in names with underscores. z3c.forms
                   # assumes - separate name parts and might convert them to .
                   # if necessary. if '-' is part of actual name and not
                   # separataor, then the name will no longer match after all -
                   # are replaced by '.'
                   'required': required}  # FIXME: should come from lens
        return self.initField(prop, fieldkw)


# TODO: move valueClass and query here ...
class Vocabulary(Graph):
    # this class may be suitable as vocabularyfactory, I am just not sure how
    # to register it properly, as the connection to the triple store might not
    # yet be available at that time.

    def __init__(self, *av, **kw):
        super(Vocabulary, self).__init__(*av, **kw)

    def __call__(self):
        query = self.value(self.identifier, Z3C['query'])
        classuri = self.value(self.identifier, Z3C['valueClass'])
        if classuri is not None:
            return SparqlInstanceVocabularyFactory()(classuri)
        else:
            # assume a query has been given
            return SparqlVocabularyFactory()(query)

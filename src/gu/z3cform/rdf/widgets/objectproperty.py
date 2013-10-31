from z3c.form.browser.widget import HTMLFormElement
from z3c.form.widget import FieldWidget, Widget
from z3c.form.interfaces import IFormLayer, IFieldWidget, ISubformFactory, NO_VALUE, IValidator, IDataConverter, IGroup, ISubForm
from ordf.graph import Graph
from rdflib import URIRef
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectPropertyWidget
from gu.z3cform.rdf.interfaces import IRDFObjectPropertyField, IORDF
from zope.component import queryMultiAdapter, adapter, getMultiAdapter, getUtility
from zope.pagetemplate.interfaces import IPageTemplate
from zope.interface import implementer
from zope.schema import ValidationError
from z3c.form.error import MultipleErrors


@implementer(IRDFObjectPropertyWidget)
# TODO: should split this widget into non html and html part
class RDFObjectPropertyWidget(HTMLFormElement, Widget):

    subform = None

    # self.context ... set by FieldWidgets.content which is form.getContent() and usually the same as form.context

    def render(self):
        """See z3c.form.interfaces.IWidget."""
        # TODO: render the layout wrapper here and let the subform do the rest
        template = self.template
        if template is None:
            template = queryMultiAdapter(
                (self.context, self.request, self.form, self.field, self,
                 None ), # Dummy object),
                IPageTemplate, name=self.mode)
            if template is None:
                template = getMultiAdapter(
                    (self.context, self.request, self.form, self.field, self),
                    IPageTemplate, name=self.mode)
        return template(self)

    def _getForm(self):
        # TODO: check if we create the form multiple times during one request
        #       and if yes, find out what needs to be updated on repeated calls
        #       e.g. context, value, mode, etc....
        # The widget provides a context for the form
        context = None
        if self.value:
            # TODO: use field here
            uri = URIRef(self.value)
            handler = getUtility(IORDF).getHandler()
            context = handler.get(URIRef(uri))
        else:
            identifier = getUtility(IORDF).generateURI()
            context = Graph(identifier=identifier)
            self.value = unicode(identifier)

        form = getattr(self, 'form', None)

        # get parent main form (we might be within a group and only main form has buttons)
        while form is not None:
            if IGroup.providedBy(form):
                form = form.__parent__
            elif IRDFObjectPropertyWidget.providedBy(form):
                form = form.form
            elif ISubForm.providedBy(form):
                form = form.__parent__
            else:
                break

        subformfactory = getMultiAdapter(
            (context,  self.request,
             form, self, self.field), ISubformFactory)
        subform = subformfactory()
        # TODO: pass on all widget properties to the form
        subform.ignoreContext = self.ignoreContext
        subform.mode = self.mode
        return subform

    def updateSubForm(self):
        self.subform = self._getForm()
        self.subform.update()

    def update(self):
        # get value for widget
        super(RDFObjectPropertyWidget, self).update()
        # update subform once we have a widget value
        self.updateSubForm()
        # let's update our value based on the subform update
        # TODO: maybe check if value is already set? and also ignoreContext, ignoreRequest etc...
        if not any((w.value for w in self.subform.widgets.values())):
            self.value = None
        else:
            self.value = unicode(self.subform.context.identifier)
        # after updating subform we should have an updated self.value as well

    def extract(self):
        data = super(RDFObjectPropertyWidget, self).extract()
        if data is NO_VALUE or not self.subform:
            # NO_VALUE ... there was no data submitted for this widget (hidden field missing)
            # subform ... widget has not finished updating yet
            return data
        # check the subform for errors as well
        formdata, formerrors = self.subform.extractData()
        if formerrors:
            raise MultipleErrors(formerrors)
        # if we had no subgraph before then we are not able to extract anything from the request
        # so we have to look at the subform, whether there is data available or not
        has_form_values = any(formdata.values())
        if not data and has_form_values:
            data = unicode(self.subform.context.identifier)
        # if we had some data but now the subform is empty we want to remove everything
        if data and not has_form_values:
            data = u''
        # TODO: check if the logic above still holds even if we don't apply data yet (e.g. form reload duo to adding new add widget in another unrelated multiwidget)
        return data


@adapter(IRDFObjectPropertyField, IFormLayer)
@implementer(IFieldWidget)
def RDFObjectPropertyFieldWidget(field, request):
    """IFieldWidget factory for IObjectPropertyWidget."""
    return FieldWidget(field, RDFObjectPropertyWidget(request))

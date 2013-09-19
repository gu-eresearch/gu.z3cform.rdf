from z3c.form.browser.object import ObjectWidget
from z3c.form.widget import FieldWidget, Widget
from z3c.form.interfaces import IFormLayer, IFieldWidget, ISubformFactory, NO_VALUE, IValidator, IDataConverter
from ordf.graph import Graph
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectWidget
from gu.z3cform.rdf.interfaces import IRDFObjectField
from zope.component import queryMultiAdapter, adapter, getMultiAdapter
from zope.pagetemplate.interfaces import IPageTemplate
from zope.interface import implementer
from zope.schema import ValidationError
from z3c.form.error import MultipleErrors


@implementer(IRDFObjectWidget)
class RDFObjectWidget(ObjectWidget):

    def _getForm(self, content):
        form = getattr(self, 'form', None)
        # TODO: check whether we will need all of it?
        self.subform = getMultiAdapter(
            (content, self.request, self.context,
             form, self, self.field, Graph()),
            ISubformFactory)()

    def render(self):
        """See z3c.form.interfaces.IWidget."""
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
                #return ObjectWidget.render(self)  # skip ObjectWidgets render method
        return template(self)

    def applyValue(self, widget, value=NO_VALUE):
        """Validate and apply value to given widget
        """
        # TODO: check, this method might not be necessary

        converter = IDataConverter(widget)
        try:
            getMultiAdapter(
                (self.context,
                 self.request,
                 self.form,
                 getattr(widget, 'field', None),
                 widget),
                IValidator).validate(value)

            widget.value = converter.toWidgetValue(value)
        except (ValidationError, ValueError):
            # on exception, setup the widget error message
            # set the wrong value as value
            # the widget itself ought to cry about the error
            widget.value = value

    @apply
    def value():
        """This invokes updateWidgets on any value change e.g. update/extract."""
        def get(self):
            #value (get) cannot raise an exception, then we return insane values
            try:
                self.setErrors=True
                return self.extract()
            except MultipleErrors:
                # FIXME: ... we are dealing with a graph
                LOG.error("Need to extract dat afrom widgets here")
                return value
                # value = {}
                # for name in self.subform.fields:
                #     value[name] = self.subform.widgets[name].value
                # return value
        def set(self, value):
            # FIXME: think through, ... where can thi scome form, how can it change ?
            # might be a dcit here:
            self._value = value
            self.updateWidgets()

            # ensure that we apply our new values to the widgets
            # TODO: check,. this sholud already be applied in updateWidgets?
            # if value is not NO_VALUE:
            #     for name in self.subform.fields:  #zope.schema.getFieldNames(self.field.schema):
            #         self.applyValue(self.subform.widgets[name],
            #                         value.get(name, NO_VALUE))

        return property(get, set)


@adapter(IRDFObjectField, IFormLayer)
@implementer(IFieldWidget)
def RDFObjectFieldWidget(field, request):
    """IFieldWidget factory for IObjectWidget."""
    return FieldWidget(field, RDFObjectWidget(request))

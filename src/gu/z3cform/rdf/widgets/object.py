from z3c.form.browser.object import ObjectWidget
from z3c.form.widget import FieldWidget, Widget
from z3c.form.interfaces import IFormLayer, IFieldWidget, ISubformFactory, NO_VALUE, IValidator, IDataConverter
from ordf.graph import Graph
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectWidget
from gu.z3cform.rdf.interfaces import IRDFObjectField
from zope.component import queryMultiAdapter, adapter, getMultiAdapter
from zope.pagetemplate.interfaces import IPageTemplate
from zope.interface import implements, implementer
from zope.schema import ValidationError
from z3c.form.error import MultipleErrors



class RDFObjectWidget(ObjectWidget):

    implements(IRDFObjectWidget)

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
            # import ipdb; ipdb.set_trace()
            # if value is not NO_VALUE:
            #     for name in self.subform.fields:  #zope.schema.getFieldNames(self.field.schema):
            #         self.applyValue(self.subform.widgets[name],
            #                         value.get(name, NO_VALUE))

        return property(get, set)



    def update(self):
        # TODO: remove, same as base
        #       ... get widget value form field value and generatu sub widgets
        
        #very-very-nasty: skip raising exceptions in extract while we're updating
        self._updating = True
        try:
            super(ObjectWidget, self).update()
            self.updateWidgets(setErrors=False)
        finally:
            self._updating = False


    def updateWidgets(self, setErrors=True):
        # TODO: remove, same as base
        #       ... generate gorm and using current value
        if self._value is not NO_VALUE:
            self._getForm(self._value)
        else:
            self._getForm(None)
            self.subform.ignoreContext = True

        self.subform.update()
        if setErrors:
            self.subform._validate()

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


            

@adapter(IRDFObjectField, IFormLayer)
@implementer(IFieldWidget)
def RDFObjectFieldWidget(field, request):
    """IFieldWidget factory for IObjectWidget."""
    return FieldWidget(field, RDFObjectWidget(request))

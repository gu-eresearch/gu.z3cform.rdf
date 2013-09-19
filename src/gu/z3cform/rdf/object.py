from z3c.form.interfaces import ISubformFactory, IFormLayer
from zope.interface import Interface, implementer
from zope.component import adapter
from gu.z3cform.rdf.interfaces import IRDFObjectField
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectWidget
from gu.z3cform.rdf.converter import BaseDataConverter, RDFObjectSubForm


@implementer(ISubformFactory)
@adapter(Interface,  # widget value
         IFormLayer,  # request
         Interface,  # widget context
         Interface,  # form
         IRDFObjectWidget,  # widget
         IRDFObjectField,  # field
         Interface,  # field.schema
         )
class SubformAdapter(object):
    """Most basic-default subform factory adapter"""

    factory = RDFObjectSubForm

    def __init__(self, context, request, widgetContext, form,
                 widget, field, schema):
        self.context = context  # context for this form
        self.request = request  # request
        self.widgetContext = widgetContext  # main context
        self.form = form  # main form
        self.widget = widget  # the widget tha manages this form
        self.field = field  # the field to attach the whole thing to
        self.schema = schema  # we don't use this

    def __call__(self):
        obj = self.factory(self.context, self.request, self.widget)
        return obj

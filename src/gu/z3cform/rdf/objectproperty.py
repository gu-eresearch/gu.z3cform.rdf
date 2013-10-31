from z3c.form.interfaces import ISubformFactory, IFormLayer, NO_VALUE, ISubForm, IHandlerForm, IActionForm, IActionHandler, IAfterWidgetUpdateEvent, IActions, IEditForm, IAddForm
from z3c.form import button, form
from z3c.form.field import Fields
from zope.interface import Interface, implementer
from zope.component import adapter, getUtility, queryMultiAdapter
from gu.z3cform.rdf.interfaces import IRDFObjectPropertyField, IORDF
from gu.z3cform.rdf.widgets.interfaces import IRDFObjectPropertyWidget
from ordf.graph import _Graph,  Graph
from rdflib import URIRef
from gu.z3cform.rdf.fresnel import getFieldsFromFresnelLens
from gu.z3cform.rdf.schema import URIRefField

# TODO: move somewhere else
@implementer(ISubForm, IHandlerForm)
class RDFObjectPropertySubForm(form.BaseForm):

    formErrorsMessage = 'There were some errors.'
    successMessage = 'Data successfully updated.'
    noChangesMessage = 'No changes were applied.'

    def __init__(self, context, request, parentWidget):
        self.context = context
        self.request = request
        self.__parent__ = parentWidget  # It's a widget
        # make sure we have a unique name for everything
        self.prefix = parentWidget.name

    # hookup this handler with whatever button submits the main form
    def handleApply(self, action):
        # TODO: check _subforms for additional applies
        data, errors = self.widgets.extract()
        if errors:
            self.status = self.formErrorsMessage
            return
        content = self.getContent()
        changed = form.applyChanges(self, content, data)
        if changed:
            #zope.event.notify(
            #    zope.lifecycleevent.ObjectModifiedEvent(content))
            self.status = self.successMessage
        else:
            self.status = self.noChangesMessage
        # in case we are a ISubFormAware subform we can gat an IActions object
        # FIXME: may not have _subforms attribute if there are no further subforms
        for subform in getattr(self, '_subforms', []):
            handler = queryMultiAdapter(
                (subform, self.request, subform.getContent(), action),
                 interface = IActionHandler)
            if handler is not None:
                subresult = handler()
                # TODO: interpret subresult ....
                #       error handling, succes, feed back changes, etc...

    def update(self):
        self.setupFields()
        super(RDFObjectPropertySubForm, self).update()

    def setupFields(self):
        # TODO: can I set them up without cotext? (would miss out on allProperties though)
        context = self.getContent()
        lens = self.__parent__.field.lens
        if lens is not None:
            _, self.fields = getFieldsFromFresnelLens(lens, context,
                                                 context.identifier)
        else:
            # TODO: raise error here?, without lens we can't do much
            self.fields = Fields()

        # TODO: maybe I won't need this here, as the widget could track it
        # from zope.schema import TextLine
        # from z3c.form.interfaces import HIDDEN_MODE
        # idfields = Fields(URIRefField(__name__='identifier',
        #                            readonly=True,
        #                            required=False))
        # idfields['identifier'].mode = HIDDEN_MODE
        # self.fields += idfields

    def getContent(self):
        val = None
        # if the widget set a context for use, use it
        if not self.ignoreContext and self.context:
            # context is the graph the widget got for us
            val = self.context
        # if is set up so that we always should have a context
        else:
            # this wolud be a place to do custom stuff in case we ignore context
            # or context is none
            val = self.context
        return val


@implementer(ISubformFactory)
class RDFObjectPropertySubformFactory(object):

    def __init__(self, context, request, form, widget, field):
        self.context = context
        self.request = request
        self.form = form
        self.widget = widget
        self.field = field

    def __call__(self):
        return self.subformclass(self.context, self.request, self.widget)


class EditRDFObjectPropertySubForm(RDFObjectPropertySubForm):

    @button.handler(form.EditForm.buttons['apply'])
    def handleApply(self, action):
        super(EditRDFObjectPropertySubForm, self).handleApply(action)

@adapter(Interface,
         IFormLayer,
         IEditForm,
         IRDFObjectPropertyWidget,
         IRDFObjectPropertyField)
class EditRDFObjectPropertySubformFactory(RDFObjectPropertySubformFactory):
    subformclass = EditRDFObjectPropertySubForm


class AddRDFObjectPropertySubForm(RDFObjectPropertySubForm):

    @button.handler(form.AddForm.buttons['add'])
    def handleApply(self, action):
        super(AddRDFObjectPropertySubForm, self).handleApply(action)

@adapter(Interface,
         IFormLayer,
         IAddForm,
         IRDFObjectPropertyWidget,
         IRDFObjectPropertyField)
class AddRDFObjectPropertySubformFactory(RDFObjectPropertySubformFactory):
    subformclass = AddRDFObjectPropertySubForm


from zope.interface import Interface, alsoProvides
class ISubformAware(Interface):
    pass


@adapter(IAfterWidgetUpdateEvent)
def SubformHandlerSubscriber(event):
    widget = event.widget
    if not IRDFObjectPropertyWidget.providedBy(widget):
        return
    # look for parent form which is able to handle actions (skip groupform containers)
    # TODO: this checks just one level:
    # TODO: protect against double execution for same widget
    parentform = widget.form
    if not IHandlerForm.providedBy(parentform):
        parentform = parentform.__parent__
    subforms = getattr(parentform,  '_subforms', None)
    if subforms is None:
        subforms = parentform._subforms = []
    subforms.append(widget.subform)
    alsoProvides(parentform, ISubformAware)


from z3c.form.button import ButtonActions
from zope.event import notify
from z3c.form.action import ActionErrorOccurred, ActionSuccessful
from z3c.form.interfaces import IActionHandler, ActionExecutionError

@adapter(
        ISubformAware,  # form
        Interface,      # request
        Interface)      # content
class SubformAwareActions(ButtonActions):

    def execute(self):
        """See z3c.form.interfaces.IActions."""
        # self.form ... the form too look for subforms
        # self.form.subforms[...].handlers
        for action in self.executedActions:
            # action.field -> Button
            # action.field.__name__ -> 'save'
            # action.name -> 'form.buttons.save'
            # action.form =? self.form
            handler = queryMultiAdapter(
                (self.form, self.request, self.content, action),
                interface=IActionHandler)
            if handler is not None:
                try:
                    result = handler()
                    # result usually None?
                    # we are here, so self.form should have subforms:
                    for subform in self.form._subforms:
                        handler = queryMultiAdapter(
                            (subform, self.request, subform.getContent(), action),
                            interface = IActionHandler)
                        if handler is not None:
                            subresult = handler()
                except ActionExecutionError as error:
                    notify(ActionErrorOccurred(action, error))
                else:
                    notify(ActionSuccessful(action))
                    return result

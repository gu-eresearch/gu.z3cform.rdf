from z3c.form.browser.orderedselect import OrderedSelectWidget
from z3c.form.browser.select import SelectWidget
from z3c.form.browser import widget
from z3c.form.widget import FieldWidget
from collections import defaultdict
from zope.interface import implements
from gu.z3cform.rdf.widgets.interfaces import IGroupedSelectWidget
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.i18n import translate


class OrderedGroupedSelectWidget(OrderedSelectWidget):

    items = None

    def update(self):
        super(OrderedSelectWidget, self).update()
        widget.addFieldClass(self)
        self.items = defaultdict(list)

        for count, term in enumerate(self.terms):
            self.items[term.optgroup].append(self.getItem(term, count))
        self.selectedItems = [
            self.getItem(self.terms.getTermByToken(token), count)
            for count, token in enumerate(self.value)]
        self.notselectedItems = self.deselect()


class GroupedSelectWidget(SelectWidget):

    implements(IGroupedSelectWidget)

    klass = u'group-select-widget'
    css = u'select'
    prompt = False

    def items(self):
        # put items in optgroups
        # Note: this assumes, that terms have a group attribute.
        if self.terms is None:  # update() has not been called yet
            return ()
        optgroups = defaultdict(list)
        if (not self.required or self.prompt) and self.multiple is None:
            message = self.noValueMessage
            if self.prompt:
                message = self.promptMessage
            optgroups[''].append({
                'id': self.id + '-novalue',
                'value': self.noValueToken,
                'content': message,
                'selected': self.value == [],
                })

        ignored = set(self.value)

        def addItem(idx, group, term, prefix=''):
            selected = self.isSelected(term)
            if selected:
                ignored.remove(term.token)
            id = '%s-%s%i' % (self.id, prefix, idx)
            content = term.token
            if ITitledTokenizedTerm.providedBy(term):
                content = translate(
                    term.title, context=self.request, default=term.title)
            optgroups[group].append(
                {'id': id, 'value': term.token, 'content': content,
                 'selected': selected})

        idx = 0
        # FIXME: self.terms.terms ... self.terms sholud be tree aware?
        for term, values in self.terms.terms.items():
            # terms are keys ... values may be an additional hierarchy level
            for subterm in values:
                addItem(idx, term.title or term.value, subterm)
                idx += 1

        if ignored:
            # some values are not displayed, probably they went away from the vocabulary
            for idx, token in enumerate(sorted(ignored)):
                try:
                    term = self.terms.getTermByToken(token)
                except LookupError:
                    # just in case the term really went away
                    continue

                addItem(idx, term, prefix='missing-')
        return optgroups


# @zope.component.adapter(
#     zope.schema.interfaces.IUnorderedCollection, interfaces.IFormLayer)
# @zope.interface.implementer(interfaces.IFieldWidget)
def GroupedSelectFieldWidget(field, request):
    """IFieldWidget factory for SelectWidget."""
    widget = FieldWidget(field, GroupedSelectWidget(request))
    widget.size = 5
    widget.multiple = 'multiple'
    return widget


# @zope.component.adapter(
#     zope.schema.interfaces.IUnorderedCollection,
#     zope.schema.interfaces.IChoice, interfaces.IFormLayer)
# @zope.interface.implementer(interfaces.IFieldWidget)
# def CollectionGroupedSelectFieldWidget(field, value_type, request):
#     """IFieldWidget factory for SelectWidget."""
#     return SelectFieldWidget(field, None, request)

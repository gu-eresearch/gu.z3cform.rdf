import os.path
import re


def guessRDFFileFormat(format, contentType, filename):
    """
    determine file format:

    if format is not known, check contentType and filename

    TODO: take contentType into account
    """
    if format.lower() not in ('n3', 'xml'):
        ext = os.path.splitext(filename)[1].lower()
        if ext in ('.n3',):
            return u"n3"
        elif ext in ('.rdf', '.owl'):
            return u"xml"
        return None
    return format

# !application/rdf+xml - !xml
# text/n3 ... !n3
# text/plain... !nt
# !application/xhtml+xml ... !rdfa
# !text/html ... !rdfa


class Period(object):
    """
    Parse DCMI period strings and provide values as attributes.

    Format set period values as valid DCMI period.

    FIXME: currently uses date strings as is and does not try to interpret them.
           the same for formatting. date's have to be given as properly formatted strings.
    """

    start = end = scheme = name = None

    def __init__(self, str):
        '''
        TODO: assumes str is unicode
        '''
        sm = re.search(r'start=(.*?);', str)
        if sm:
            self.start = sm.group(1)
        sm = re.search(r'scheme=(.*?);', str)
        if sm:
            self.scheme = sm.group(1)
        sm = re.search(r'end=(.*?);', str)
        if sm:
            self.end = sm.group(1)
        sm = re.search(r'name=(.*?);', str)
        if sm:
            self.name = sm.group(1)

    def __unicode__(self):
        parts = []
        if self.start:
            parts.append("start=%s;" % self.start)
        if self.end:
            parts.append("end=%s;" % self.end)
        if self.name:
            parts.append("name=%s;" % self.name)
        if self.scheme:
            parts.append("scheme=%s;" % self.scheme)
        return u' '.join(parts)

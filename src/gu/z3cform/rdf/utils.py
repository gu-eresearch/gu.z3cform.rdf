import os.path

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

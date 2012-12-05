"""Response writers, which take a template context & return a Response object.

Where much of tango stays in pure Python, data, and templating concerns, the
writers are decidedly aware of HTTP, getting request objects and returning
response objects which implement HTTP semantics. Writers are not "view"
functions as typically found in Python web programming, such that the view of
the data has already been processed in the stash. Instead, a writer is given
the pre-processed data from the shelf along with the request seeking the
content, and the writer returns a response after rendering the context into a
serializable form. The response could be anything valid in HTTP/WSGI, but
typically is a string with a matching content type (mimetype).

Writers are initialized with Tango instances in order to get access to:

* app.config
* app.response_class
* app.logger
* app.shelf
"""

import datetime
import json
import mimetypes

from flask import render_template


class BaseWriter(object):
    """A response writer, given a template context.

    Initialize an instance of a BaseWriter subclass, then call it.

        writer = Writer(app)
        writer(request, template_context)

    Set mimetype attribute as appropriate or to None to use app's default,
    i.e. app.response_class.default_mimetype.

    A subclass must implement a write method:
    >>> class IncompleteWriter(BaseWriter):
    ...     "Does not implement the write method."
    ...
    >>> incomplete = IncompleteWriter(None)
    >>> incomplete(None, test_context)
    Traceback (most recent call last):
       ...
    NotImplementedError: Where is this writer's write method?
    >>>
    """

    # Default Content-Type to use in the HTTP response
    mimetype = None

    def __init__(self, app):
        self.app = app

    def __call__(self, request, context):
        response = self.write(request, context)
        if self.mimetype is not None:
            # Set default_mimetype to allow write method to set mimetype attr.
            response.default_mimetype = self.mimetype
            response.mimetype = self.mimetype
        return response

    def write(self, request, context):
        raise NotImplementedError("Where is this writer's write method?")


class TextWriter(BaseWriter):
    """Write a template context as a simple string representation.

    Test:
    >>> from tango.app import Tango
    >>> text = TextWriter(Tango(__name__))
    >>> response = text(None, test_context)
    >>> type(response)
    <class 'tango.http.Response'>
    >>> print response.data # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
    {'answer': 42, 'count': ['one', 'two'],
     'lambda': <function <lambda> at 0x...>,
     'adict': {'second': 2, 'first': 1}, 'title': 'Test Title'}
    >>>
    """

    mimetype = 'text/plain'

    def write(self, request, context):
        return self.app.response_class(unicode(context))


class JsonWriter(BaseWriter):
    """Write a template context in JSON format.

    Note that this writer skips context keys not of a basic type and context
    values which cannot be serialized.

    See Python's json module documentation for more information.

    Test:
    >>> from tango.app import Tango
    >>> json = JsonWriter(Tango(__name__))
    >>> response = json(None, test_context)
    >>> type(response)
    <class 'tango.http.Response'>
    >>> response.mimetype
    'application/json'
    >>> print response.data # doctest:+NORMALIZE_WHITESPACE
    {"answer": 42, "count": ["one", "two"],
     "adict": {"second": 2, "first": 1}, "title": "Test Title"}
    >>>

    This writer handles date/datetime objects using the formats in app.config.
    >>> import datetime
    >>> context = {"answer": 42, "adate": datetime.date(2012, 9, 13),
    ...            "adatetime": datetime.datetime(2012, 9, 13, 14, 40)}
    >>> app = Tango(__name__)
    >>> json = JsonWriter(app)
    >>> print json(None, context).data
    {"answer": 42, "adate": "2012-09-13", "adatetime": "2012-09-13 14:40:00"}
    >>> app.config['DEFAULT_DATETIME_FORMAT'] = '%m/%d/%Y %H:%M'
    >>> app.config['DEFAULT_DATE_FORMAT'] = '%d %b %Y'
    >>> print json(None, context).data
    {"answer": 42, "adate": "13 Sep 2012", "adatetime": "09/13/2012 14:40"}
    >>>
    """

    mimetype = 'application/json'

    def write(self, request, context):
        # Trim context down to those values which are JSON serializable.
        trimmed_context = {}
        for key, value in context.items():
            try:
                # Format datetime & date objects into strings.
                # If strf format is invalid, will raise a TypeError.
                if isinstance(value, datetime.datetime):
                    format = self.app.config['DEFAULT_DATETIME_FORMAT']
                    if format is not None:
                        value = value.strftime(format)
                    else:
                        value = str(value)
                if isinstance(value, datetime.date):
                    format = self.app.config['DEFAULT_DATE_FORMAT']
                    if format is not None:
                        value = value.strftime(format)
                    else:
                        value = str(value)

                # Trigger a TypeError if this value is not JSON serializable.
                json.dumps({key: value})

                trimmed_context[key] = value
            except TypeError:
                # This value is not json serializable.
                self.app.logger.warn(
                    "Unable to JSON serialize "
                    "'%(key)s' with value: %(value)r" % locals()
                )
        return self.app.response_class(json.dumps(trimmed_context))


class TemplateWriter(BaseWriter):
    """Write a template context to named template. Requires an app in context.

    The intent is to instantiate a TemplateWriter per template name, ready to
    register as a writer under the name of the template.

    Test:
    >>> from tango.app import Tango
    >>> from flask import request
    >>> app = Tango.build_app('simplesite')
    >>> ctx = app.test_request_context()
    >>> ctx.push()
    >>> template_writer = TemplateWriter(app, 'index.html')
    >>> response = template_writer(request, test_context)
    >>> '<title>Test Title</title>' in response.data
    True
    >>> template_writer.mimetype
    'text/html'
    >>>

    The template's mimetype is guessed based on the file extension.
    >>> text_template_writer = TemplateWriter(app, 'index.txt')
    >>> print text_template_writer(request, test_context).data
    Test Title
    >>> text_template_writer.mimetype
    'text/plain'
    >>> xml_template_writer = TemplateWriter(app, 'index.xml')
    >>> response = xml_template_writer(request, test_context)
    >>> '<title>Test Title</title>' in response.data
    True
    >>> xml_template_writer.mimetype
    'application/xml'
    >>> ctx.pop()
    >>>
    """

    mimetype = 'text/html'

    def __init__(self, app, template_name):
        super(TemplateWriter, self).__init__(app)
        self.template_name = template_name
        basename = self.template_name.rsplit('/', 1)[-1]
        guessed_type, guessed_encoding = mimetypes.guess_type(basename)
        if guessed_type:
            self.mimetype = guessed_type

    def write(self, request, context):
        rendered = render_template(self.template_name, **context)
        return self.app.response_class(rendered)


test_context = {'answer': 42, 'count': ['one', 'two'], 'title': 'Test Title',
                'lambda': lambda x: None, 'adict': {'first': 1, 'second': 2}}

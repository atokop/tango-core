"Core Tango classes for creating applications from Tango sites."

from flask import Flask, request
from jinja2 import Environment, PackageLoader, TemplateNotFound
from werkzeug import LocalProxy as Proxy

from tango.errors import NoSuchWriterException
from tango.imports import module_is_package
from tango.writers import TemplateWriter, TextWriter, JsonWriter


__all__ = ['Tango', 'request', 'Proxy']


class Tango(Flask):
    "Application class for a Tango site."

    def __init__(self, import_name, *args, **kwargs):
        if module_is_package(import_name):
            # Flask.__init__ v0.9 sets static path based on sys.modules.
            # As such, import the package here to ensure it's in sys.modules.
            __import__(import_name)
        Flask.__init__(self, import_name, *args, **kwargs)
        self.set_default_config()
        self.writers = {}
        self.register_default_writers()

        if self.config.get('REQUEST_CLASS') is not None:
            self.request_class = self.config['REQUEST_CLASS']

        if self.config.get('RESPONSE_CLASS') is not None:
            self.response_class = self.config['RESPONSE_CLASS']

        # The writer to use when no writer is specified in the stash route.
        # Initialized as None here, as this is provided in config.py.
        #
        # Configure the default writer on first call to get_writer in order to
        # allow the default writer class to be configured in the application's
        # config after Tango instance creation.
        self.default_writer = None

    def set_default_config(self):
        self.config.from_object('tango.config')

    def create_jinja_environment(self):
        options = dict(self.jinja_options)
        if 'autoescape' not in options:
            options['autoescape'] = self.select_jinja_autoescape
        return Environment(loader=TemplateLoader(self.import_name), **options)

    def register_default_writers(self):
        self.register_writer('text', TextWriter(self))
        self.register_writer('json', JsonWriter(self))
        # The default writer (key: None) is configured in get_writer.

    def register_writer(self, name, writer):
        self.writers[name] = writer

    def get_writer(self, name):
        # Do not register writer for None, in case of config change.
        if name is None:
            if self.default_writer is None:
                # Bootstrap default_writer instance with class given in config.
                self.default_writer = self.config['DEFAULT_WRITER_CLASS'](self)
            return self.default_writer
        writer = self.writers.get(name)
        if writer is not None:
            return writer
        # A writer prefixed with 'template:' is for a template.
        if name.startswith('template:'):
            template_name = name.replace('template:', '', 1)
            writer = TemplateWriter(self, template_name)
            self.register_writer(name, writer)
            return writer
        raise NoSuchWriterException(name)

    @property
    def shelf(self):
        return self.config['SHELF_CONNECTOR_CLASS'](self)

    def build_view(self, route, **options):
        site = route.site
        rule = route.rule
        writer = self.get_writer(route.writer_name)
        def view(*args, **kwargs):
            # Pass the actual request object, and not a proxy.
            return writer(request._get_current_object(),
                          self.shelf.get(site, rule))
        view.__name__ = route.rule
        return self.route(route.rule, **options)(view)


class Route(object):
    "Route metadata for a Tango stashable context module."

    # required site field in the header
    site = None

    # required url rule/path of this route
    rule = None

    # required dict of variable names & values imported into route's context
    # an export's value is None when it has not yet been imported
    exports = None

    # list of exports which are statically set in header
    static = None

    # name of writer to use in rendering route, may be template name
    writer_name = None

    # context as exported by stashable module, for template or serialization
    context = None

    # modules from which this stash module was constructed
    modules = None

    def __init__(self, site, rule, exports, static=None, writer_name=None,
                 context=None, modules=None):
        self.site = site
        self.rule = rule
        self.exports = exports
        self.static = static
        self.writer_name = writer_name

        self.context = context
        self.modules = modules

    def __repr__(self):
        pattern = u'<Route: {0}{1}>'
        if self.writer_name is None:
            return pattern.format(self.rule, '')
        else:
            return pattern.format(self.rule, ', {0}'.format(self.writer_name))


class TemplateLoader(PackageLoader):
    """Template loader which looks for defaults.

    As Tango handles device detection, it will find templates implicitly here.

    Example:
    >>> environment = Environment(loader=TemplateLoader('simplesite'))
    >>> base = environment.get_template('base.html')
    >>> base
    <Template 'base.html'>
    >>> base.filename # doctest:+ELLIPSIS
    '.../simplesite/templates/base.html'
    >>> index = environment.get_template('index.html')
    >>> index
    <Template 'index.html'>
    >>> index.filename # doctest:+ELLIPSIS
    '.../simplesite/templates/default/index.html'
    >>>
    """

    def get_source(self, environment, template):
        try:
            return PackageLoader.get_source(self, environment, template)
        except TemplateNotFound:
            template = 'default/' + template
            return PackageLoader.get_source(self, environment, template)

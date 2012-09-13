"Core Tango classes for creating applications from Tango sites."

from flask import Flask, request
from jinja2 import Environment, PackageLoader, TemplateNotFound
from werkzeug import create_environ

from tango.errors import NoSuchWriterException
from tango.imports import module_exists, module_is_package
from tango.imports import package_submodule, namespace_segments
from tango.imports import fix_import_name_if_pyfile
from tango.stash import build_module_routes
from tango.writers import TemplateWriter, TextWriter, JsonWriter
import tango.filters


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

    @classmethod
    def get_app(cls, import_name, **options):
        """Get a Tango app object from a site by the given import name.

        This function looks for an object named app in the package or module
        matching the import name provided by the given argument, and if it does
        not exist, builds an app from the stash inside the package or module.

        Hybrid apps, those with both stash and dynamic views, start with an app
        built from stash, then extend the app through the Flask API.

        >>> Tango.get_app('simplesite') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>> Tango.get_app('testsite') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>> Tango.get_app('simplest') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>>

        Here's a simple app which has both a stash and app additions:
        >>> app = Tango.get_app('hybrid')
        >>> app # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>> app.this_was_added_after_stash
        'Hello, world!'
        >>>

        For convenience in development, particularly with shell tab completion,
        a .py module name is also accepted:
        >>> Tango.get_app('simplest.py') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>>

        Avoids import side effects:
        >>> Tango.get_app('importerror.py') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>> Tango.get_app('importerror') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>>
        """
        import_name = fix_import_name_if_pyfile(import_name)
        # If import is a package, see use it's app if it has one.
        if module_is_package(import_name):
            module = __import__(import_name)
            # Prefer app defined in module over building a new one from stash.
            app = getattr(module, 'app', None)
            if app is not None:
                return app
        # Build the app if a single-module site, or no app is found in package.
        return cls.build_app(import_name, **options)

    @classmethod
    def build_app(cls, import_name, import_stash=False, logfile=None):
        """Create a Tango application object from a Python import name.

        This function accepts three kinds of import names:

        1. a single-module name where the module is itself a stash
        2. a package name which has a submodule or sub-package named 'stash'.
        3. a dotted module name referring to a module inside a package's stash.

        In case #1, the module is a self-contained application in one .py file.

        In case #2, the package is arbitrarily laid out, but the stash module
        inside it is one or more modules conforming to Tango's stash
        conventions.

        In case #3, the module is inside a package matching case #2, but the
        import name refers to a module which by itself would otherwise match
        case #1. Case #3 is treated like case #1 with one important exception.
        Since the module is inside a package, that package is used as the
        application object's import name for the purposes of loading
        configuration directives, as stash modules are allowed to and
        encouraged to use their projects config.py. This is essential to
        shelving modules in isolation when working with a stash package with
        more than one stash module.

        Example, using a single module called simplest.py (case #1):
        >>> app = Tango.build_app('simplest')
        >>> sorted(app.url_map.iter_rules(), key=lambda rule: rule.rule)
        ... # doctest:+NORMALIZE_WHITESPACE
        [<Rule '/' (HEAD, OPTIONS, GET) -> />,
        <Rule '/static/<filename>' (HEAD, OPTIONS, GET) -> static>]
        >>>

        Example, using the simplesite module in this project (case #2):
        >>> app = Tango.build_app('simplesite')
        >>> sorted(app.url_map.iter_rules(), key=lambda rule: rule.rule)
        ... # doctest:+NORMALIZE_WHITESPACE
        [<Rule '/' (HEAD, OPTIONS, GET) -> />,
        <Rule '/static/<filename>' (HEAD, OPTIONS, GET) -> static>]
        >>>

        Example, using submodule of stash in a package with config (case #3):
        >>> app = Tango.build_app('simplesite.stash.index')
        >>> sorted(app.url_map.iter_rules(), key=lambda rule: rule.rule)
        ... # doctest:+NORMALIZE_WHITESPACE
        [<Rule '/' (HEAD, OPTIONS, GET) -> />,
        <Rule '/static/<filename>' (HEAD, OPTIONS, GET) -> static>]
        >>>

        Example, using submodule in the stash in a package without config
        (case #3 but identical to case #1):
        >>> app = Tango.build_app('testsite.stash.package.module')
        >>> sorted(app.url_map.iter_rules(), key=lambda rule: rule.rule)
        ... # doctest:+NORMALIZE_WHITESPACE
        [<Rule '/index.json' (HEAD, OPTIONS, GET) -> /index.json>,
        <Rule '/static/<filename>' (HEAD, OPTIONS, GET) -> static>]
        >>>

        For convenience in development, particularly with shell tab completion,
        a .py module name is also accepted:
        >>> Tango.build_app('simplest.py') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>>

        Avoids import side effects:
        >>> Tango.build_app('importerror.py') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>> Tango.build_app('importerror') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>>
        """
        import_name = fix_import_name_if_pyfile(import_name)

        # Initialize application. See docstring above for construction logic.
        app = None
        package_name, module_name = package_submodule(import_name)
        if package_name and module_name:
            # import_name points to submodule, look for package config.
            root_package_name = namespace_segments(import_name)[0]
            if module_exists(root_package_name + '.config'):
                app = cls(root_package_name)
                app.config.from_object(root_package_name + '.config')

        if app is None:
            app = cls(import_name)

        # Check for a site config.
        if module_exists(import_name + '.config'):
            app.config.from_object(import_name + '.config')

        # Push app context onto request stack for use in initialization.
        # Use `with` or try-finally, ensure context is popped in case of error.
        with app.request_context(create_environ()):
            # Load Tango filters. Only needed for packages; single modules do
            # not have implicit templates.
            if module_is_package(import_name):
                tango.filters.init_app(app)

            build_options = {'import_stash': import_stash}
            build_options['logfile'] = logfile
            if module_exists(import_name + '.stash'):
                module = __import__(import_name, fromlist=['stash']).stash
                app.routes = build_module_routes(module, **build_options)
            else:
                app.routes = build_module_routes(import_name, **build_options)

            # Stitch together context, template, and path.
            for route in app.routes:
                app.build_view(route)

        @app.context_processor
        def process_view_args():
            """Put view args into template context for tango template writers.

            The Flask Request object has a dictionary of the request handler
            function's arguments, but this is None when there are no view
            arguments. A Flask context processor must always return a
            dictionary.

            http://flask.pocoo.org/docs/api/#flask.Request.view_args
            """
            if request.view_args is None:
                return {}
            return request.view_args

        return app

    def shelve(self, logfile=None):
        """Shelve the route contexts of this app.

        Does not return anything, and inherently has side-effects:
        >>> Tango.build_app('simplest').shelve()
        >>>
        """
        for route in self.routes:
            site, rule, context = route.site, route.rule, route.context
            if logfile is not None:
                logfile.write('Stashing {0} {1} ... '.format(site, rule))
            self.shelf.put(site, rule, context)
            if logfile is not None:
                logfile.write('done.\n')

    @classmethod
    def shelve_by_name(cls, name, logfile=None):
        """Shelve the route contexts of an app matching import name.

        Does not return anything, and inherently has side-effects:
        >>> Tango.shelve_by_name('simplest') # doctest:+ELLIPSIS
        <tango.app.Tango object at 0x...>
        >>>
        """
        app = cls.build_app(name, import_stash=True, logfile=logfile)
        app.shelve(logfile=logfile)
        return app


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

"Console entry point and management & development tasks for Tango framework."

from contextlib import contextmanager
import cPickle as pickle
import os
import sys
import argparse

from flask.ext.script import Command, Option
from flask.ext.script import Manager as BaseManager
from flask.ext.script import Server as BaseServer
from flask.ext.script import Shell as BaseShell

from tango.app import Tango
from tango.config import SHELVE_TIME_DIR
from tango.imports import module_exists, fix_import_name_if_pyfile
from tango.errors import ModuleNotFound
import tango

commands = []


def get_app(site, module=None):
    try:
        return Tango.get_app(module or site)
    except ModuleNotFound:
        print "Cannot locate site: '{0}'.".format(site)


def validate_site(site):
    "Verify site exists, and abort if it does not."
    site = fix_import_name_if_pyfile(site)
    if not module_exists(site):
        print "Cannot find site '%s'." % site
        # /usr/include/sysexits.h defines EX_NOINPUT 66 as: cannot open input
        sys.exit(66)
    return site


def command(function):
    """Decorator to mark a function as a Tango subcommand.

    The function's docstring is its usage string;
    its function signature, its command-line arguments.

    Note: this decorator must be inner-most to pick up function signature.
    """
    commands.append(function)
    return function


@contextmanager
def no_pyc():
    "Context manager to execute a block without writing .pyc files."
    old_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    yield
    sys.dont_write_bytecode = old_dont_write_bytecode


@command
def version():
    'Display this version of Tango.'
    # Reload tango to ensure version attribute is up to date.
    reload(tango)
    print tango.__version__


@command
def shelve(site, modified_only=False):
    "Shelve an application's stash, as a worker process."
    with no_pyc():
        # Create shelve time dir if it does not exist
        try: os.makedirs(SHELVE_TIME_DIR)
        except (IOError, OSError): pass

        shelve_time_path = os.path.join(SHELVE_TIME_DIR, site)
        os.environ['SHELVE_TIME_PATH'] = shelve_time_path
        site = validate_site(site)
        Tango.shelve_by_name(site, modified_only=modified_only, logfile=sys.stdout)
        open(os.environ['SHELVE_TIME_PATH'], 'w').close()


class Get(Command):
    """Create shelf.dat
    """
    def run(self, site, rule, module):
        app = get_app(site, module)

        if not app: return

        data =  {
            'tango_version': tango.__version__,
            'site': site,
            'module': module,
            'entries': [
                {'rule': rule,
                 'context': app.shelf.get(site, rule),
                } for site, rule in app.shelf.list(site, rule)
            ],
        }

        dat_file = open('shelf.dat', 'wb')
        dat_file.write(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
        dat_file.close()
        print 'shelf.dat created.'

    def get_options(self):
        return (
            Option('site', default=None),
            Option('rule', nargs='?', default=None),
            Option('-m', '--module', dest="module", default=None,
                   help="Provide a module name if the top level module name "
                        "differs from the site name."),
        )


class Put(Command):
    """Load a shelf.dat file onto the shelf.
    """
    def run(self, filename):
        with open(filename, 'rb') as dat_file:
            data = pickle.loads(dat_file.read())

            # TODO: Add version check here

            module = data['module']
            site = data['site']
            entries = data['entries']

            app = get_app(site, module)

            if not app: return

            for item in entries:
                rule = item['rule']
                context = item['context']
                app.shelf.put(site, rule, context)

    def get_options(self):
        return (Option('filename'),)

class Show(Command):
    """Display the contents of the shelf.
    """
    def run(self, site, rule, module, show_context, data_only):
        app = get_app(site, module)

        if not app: return

        if not data_only:
            print "Fetching {0}".format(site),
            if rule:
                print rule,
            print "from shelf ...",

        shelf_list = app.shelf.list(site, rule)

        if not data_only:
            print "done."

        for site, rule in shelf_list:
            if not data_only:
                print "Matches",
            print "{0} {1}".format(site, rule),
            if show_context:
                context = app.shelf.get(site, rule)
                if not data_only:
                    print "with context",
                print context,
            print

    def get_options(self):
        return(
            Option('site', default=None),
            Option('rule', nargs='?', default=None),
            Option('-c', '--context', action='store_true',
                   dest="show_context"),
            Option('-m', '--module', dest="module", default=None,
                   help="Provide a module name if the module name differs from"
                        " the site name."),
            Option('--data', dest="data_only", action="store_true",
                   help=argparse.SUPPRESS),
        )

class Drop(Command):
    """Drop the specified site or site/rule from the shelf.
    """
    def run(self, site, rule, module):
        app = get_app(site, module)

        if not app: return

        app.shelf.drop(site, rule)
        print 'dropped', site,
        if rule:
            print rule

    def get_options(self):
        return(
            Option('site', default=None),
            Option('rule', nargs='?', default=None),
            Option('-m', '--module', dest="module", default=None,
                   help="Provide a module name if the module name differs from"
                        " the site name."),
        )


class Source(Command):
    """Display the file or files where a shelf entry originated.
    """
    def run(self, site, rule, module, data_only):
        app = get_app(site, module)

        if not app: return

        if not data_only:
            print "Fetching source files for {0} {1} ...".format(site, rule),

        source_files = app.shelf.source(site, rule)

        if not data_only:
            print "done."

        for filepath in source_files:
            if not data_only:
                print "Comes from",
            print filepath

    def get_options(self):
        return(
            Option('site', default=None),
            Option('rule', default=None),
            Option('-m', '--module', dest="module", default=None,
                   help="Provide a module name if the module name differs from"
                        " the site name."),
            Option('--data', dest="data_only", action="store_true",
                   help=argparse.SUPPRESS),
        )



class Manager(BaseManager):
    def handle(self, prog, *args, **kwargs):
        # Chop off full path to program name in argument parsing.
        prog = os.path.basename(prog)
        return BaseManager.handle(self, prog, *args, **kwargs)


class Server(BaseServer):
    description = "Run a Tango site on the local machine, for development."

    def get_options(self):
        return (Option('site'),) + BaseServer.get_options(self)

    def handle(self, _, site, host, port, use_debugger, use_reloader):
        site = validate_site(site)
        app = Tango.get_app(site)

        if not app: return
        app.run(host=host, port=port, debug=use_debugger,
                use_debugger=use_debugger, use_reloader=use_reloader,
                **self.server_options)


class Shell(BaseShell):
    description = 'Runs a Python shell inside Tango application context.'

    def get_options(self):
        return (Option('site'),) + BaseShell.get_options(self)

    def handle(self, _, site, *args, **kwargs):
        with no_pyc():
            site = validate_site(site)
            app = Tango.get_app(site)

            if not app: return

            Command.handle(self, app, *args, **kwargs)


def run():
    sys.path.append('.')
    # Create a Manager instance to parse arguments & marshal commands.
    manager = Manager(Tango(__name__), with_default_commands=False)

    manager.add_command('serve', Server())
    manager.add_command('shell', Shell())
    manager.add_command('show', Show())
    manager.add_command('get', Get())
    manager.add_command('put', Put())
    manager.add_command('drop', Drop())
    manager.add_command('source', Source())
    for cmd in commands:
        manager.command(cmd)
    manager.run()

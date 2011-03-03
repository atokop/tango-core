"Console entry point and management & development tasks for Tango framework."

from functools import update_wrapper
import imp
import os.path
import sys

from flaskext.script import Command, Option
from flaskext.script import Manager as BaseManager
from flaskext.script import Server as BaseServer
from flaskext.script import Shell as BaseShell

from tango.app import Tango
from tango.factory.snapshot import build_snapshot
from tango.helpers import get_module, package_submodule
import tango.factory
import tango.site
import tango.version


commands = []


def build_app(site, **options):
    """Build a Tango app object from a site name, long or short name.

    >>> build_app('default') # doctest:+ELLIPSIS
    <tango.app.Tango object at 0x...>
    >>> build_app('tango.site.default') # doctest:+ELLIPSIS
    <tango.app.Tango object at 0x...>
    >>>
    """
    packagename, base = package_submodule(site)
    if packagename is not None:
        package = get_module(packagename)
    else:
        package = tango.site
        site = 'tango.site.' + site
    try:
        imp.find_module(base, package.__path__)
    except ImportError:
        print "Cannot find site '%s'." % site
        sys.exit(7)
    return tango.factory.build_app(site, **options)


def command(function):
    """Decorator to mark a function as a Tango subcommand.

    The function's docstring is its usage string;
    its function signature, its command-line arguments.
    """
    commands.append(function)
    return function


def require_site(function):
    """Decorator to mark a function as requiring a Tango site package.

    The first argument of the decorated function is translated from a Tango
    package name into a Tango app instance, i.e.

    tango.site.default -> Tango('tango.site.default')
    """
    def wrapper(site, *args, **kwargs):
        app = build_app(site)
        return function(app, *args, **kwargs)
    update_wrapper(wrapper, function)
    return wrapper


@command
def version():
    'Display this version of Tango.'
    print tango.version.info.label


@command
def snapshot(site):
    "Build context from a Tango site package and store it into an image file."
    filename = build_snapshot(build_app(site, use_snapshot=False))
    print 'Snapshot of full template context:', filename


@command
@require_site
def build(app):
    "Build a Tango site into a collection of static files."
    # TODO: Build `tango build` command. See Flask-Static. (Basico)


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
        app = build_app(site)
        app.run(host=host, port=port, debug=use_debugger,
                use_debugger=use_debugger, use_reloader=use_reloader,
                **self.server_options)


class Shell(BaseShell):
    description = 'Runs a Python shell inside Tango application context.'

    def get_options(self):
        return (Option('site'),) + BaseShell.get_options(self)

    def handle(self, _, site, *args, **kwargs):
        app = build_app(site)
        Command.handle(self, app, *args, **kwargs)


def run():
    # Create a Manager instance to parse arguments & marshal commands.
    manager = Manager(Tango(__name__), with_default_commands=False)

    manager.add_command('serve', Server())
    manager.add_command('shell', Shell())
    for cmd in commands:
        manager.command(cmd)
    manager.run()

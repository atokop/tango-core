"Console entry point and management & development tasks for Tango framework."

import os
import sys

from flaskext.script import Command, Option
from flaskext.script import Manager as BaseManager
from flaskext.script import Server as BaseServer
from flaskext.script import Shell as BaseShell

from tango.app import Tango
from tango.factory.snapshot import build_snapshot
from tango.imports import module_exists
import tango
import tango.factory


commands = []


def build_app(site, **options):
    """Build a Tango app object from a site name, long or short name.

    >>> build_app('simplesite') # doctest:+ELLIPSIS
    <tango.app.Tango object at 0x...>
    >>> build_app('testsite') # doctest:+ELLIPSIS
    <tango.app.Tango object at 0x...>
    >>> build_app('importerror') # doctest:+ELLIPSIS
    Traceback (most recent call last):
      ...
    ImportError: No module named doesnotexist
    >>>
    """
    if not module_exists(site):
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


@command
def version():
    'Display this version of Tango.'
    print tango.__label__


@command
def snapshot(site):
    "Pull context from a stashable Tango site and store it into an image file."
    app = build_app(site, import_stash=True, use_snapshot=False)
    filename = build_snapshot(app)
    print 'Snapshot of full stashable template context:', filename


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
    sys.path.append('.')
    # Create a Manager instance to parse arguments & marshal commands.
    manager = Manager(Tango(__name__), with_default_commands=False)

    manager.add_command('serve', Server())
    manager.add_command('shell', Shell())
    for cmd in commands:
        manager.command(cmd)
    manager.run()

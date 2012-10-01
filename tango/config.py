"Default configuration for new Tango instances."

from getpass import getuser

from tango.http import Request, Response
from tango.shelf import SqliteConnector
from tango.writers import TextWriter


## Default stash shelf configuration.
# By default, use a SQLite connector. Production ready and no added dependency.
SHELF_CONNECTOR_CLASS = SqliteConnector

# Use a determinate filepath, with username to avoid permission collisions.
# Note that getuser reads environment variables and can be easily spoofed.
SHELF_SQLITE_FILEPATH = '/tmp/tango-%(user)s.db' % {'user': getuser()}

SHELVE_TIME_BASE = '/tmp/.shelve_time'

## Request/response defaults.
# Select request & response classes, for use in writers & in Flask handlers.
REQUEST_CLASS = Request
RESPONSE_CLASS = Response

# Default writer class to use, when no writer is given for a route.
DEFAULT_WRITER_CLASS = TextWriter


## Date formats.
# Default date/datetime formats, for use in template filters and JSON encoding.
# If None, uses ISO 8601 format.
#
# See strftime table here:
# http://docs.python.org/library/datetime.html#strftime-and-strptime-behavior
DEFAULT_DATETIME_FORMAT = None # For datetime.datetime objects.
DEFAULT_DATE_FORMAT = None # For datetime.date objects.

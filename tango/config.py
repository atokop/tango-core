"Core configuration directives for Tango framework and new Tango objects."

from tango.http import Request, Response
from tango.shelf import SqliteConnector
from tango.writers import TextWriter


# Default stash shelf configuration.
SHELF_CONNECTOR_CLASS = SqliteConnector
SQLITE_FILEPATH = '/tmp/tango.db'

## Request/response defaults.
# Select request & response classes, for use in writers & in Flask handlers.
REQUEST_CLASS = Request
RESPONSE_CLASS = Response

# Default writer class to use, when no writer is given for a route.
DEFAULT_WRITER_CLASS = TextWriter


# Date formats.
# Default date/datetime formats. If None, uses ISO 8601 format.
# See strftime table here:
# http://docs.python.org/library/datetime.html#strftime-and-strptime-behavior
DEFAULT_DATETIME_FORMAT = None
DEFAULT_DATE_FORMAT = None

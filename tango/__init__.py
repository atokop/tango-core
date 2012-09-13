from flask import abort, current_app, request, session

import app
import config
import errors
import imports
import tools


__all__ = ['abort', 'app', 'config', 'current_app', 'errors',
           'imports', 'request', 'session', 'tools']


# Provide simple version inspection on tango.__version__.
#
# Derive version metadata from the distribution, to allow version labels to be
# maintained in one place within this project. Version will be UNKNOWN if
# parsing the version from the distribution fails for any reason. This project
# depends on 'distribute' to provide pkg_resources.
try:
    __version__ = __import__('pkg_resources').get_distribution('Tango').version
except Exception:
    __version__ = 'UNKNOWN'

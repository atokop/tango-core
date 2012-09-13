from flask import abort, request, session

import app
import config
import errors
import factory
import imports
import tools


__all__ = ['abort', 'errors', 'request', 'session', 'app', 'build', 'config',
           'factory', 'imports', 'tools']


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

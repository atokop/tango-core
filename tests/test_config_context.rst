Testing: Application Config in Templates
========================================

Templates have a ``config`` variable in context to access the app
configuration. Let's verify this functionality.

>>> from tango.factory.app import build_app
>>> app = build_app('testsite', import_stash=False)

Set something in the configuration.

>>> app.config['SPAM'] = 'eggs'

See the configuration in the template.

>>> from flask import render_template_string
>>> with app.test_request_context():
...     render_template_string("{{ config['SPAM'] }}")
...
u'eggs'
>>>

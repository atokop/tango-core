import unittest

from tango.app import Tango


class SingleModuleAppTestCase(unittest.TestCase):

    # Tango avoids import side-effects when instantiating applications.
    # For packages, this is generally not a problem, where __init__.py is
    # often empty (yet __init__ must be imported when discovering modules).
    #
    # As a test, build an application from a module with valid metadata,
    # which raises an error at runtime.
    #
    # A note on testing style:
    # These tests could try/except, and self.fail('...') on Exception.
    # But then a developer does not get meaningful tracebacks.
    def test_importerror_app(self):
        # Must load single-module apps without import.
        # Test passes if Tango.get_app('importerror') did not error out.
        Tango.get_app('importerror')

    def test_indexerror_app(self):
        # Must load single-module apps without import.
        # Test passes if Tango.get_app('indexerror') did not error out.
        Tango.get_app('indexerror')


if __name__ == '__main__':
    unittest.main()

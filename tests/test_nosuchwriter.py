import unittest

from tango.errors import NoSuchWriterException
from tango.app import Tango


class NoSuchWriterTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_no_such_writer_exception(self):
        self.assertRaises(NoSuchWriterException,
                          Tango.build_app, 'nosuchwriter')


if __name__ == '__main__':
    unittest.main()

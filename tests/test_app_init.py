import unittest

from flask.ext.testing import TestCase

from tango.app import Tango


class AppInitTestCase(TestCase):

    def create_app(self):
        return Tango.build_app('simplesite')

    def setUp(self):
        self.client = self.app.test_client()

    def tearDown(self):
        pass

    def test_static(self):
        response = self.client.get('/static/images/willowtree-avatar.png')
        self.assertEqual(response.status_code, 200)

    def test_config(self):
        self.assertEqual(self.app.config['DEFAULT_DATE_FORMAT'], '%Y-%m-%d')


if __name__ == '__main__':
    unittest.main()

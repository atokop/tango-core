class ConnectorCommonTests(object):
    "Mixin for common tests in shelf connector implementations."

    def smoke_test(self, reason='smoke'):
        # Use reason argument to produce a unique unittest failure message.
        self.assertEquals(self.connector.get('', ''), {})

    def test_get_keymiss(self):
        self.assertEquals(self.connector.get('site', 'rule'), {})

    def test_new_item(self):
        self.assertEquals(self.connector.get('site', 'rule'), {})
        item = {'spam': 'eggs'}
        self.connector.put('site', 'rule', item)
        self.assertEquals(self.connector.get('site', 'rule'), item)

    def test_update_item(self):
        self.test_new_item()
        item = {'spam': 'eggs'}
        update = {'spam': 'eggs', 'foo': 'bar'}
        self.connector.put('site', 'rule', update)
        self.assertEqual(self.connector.get('site', 'rule'), update)
        self.assertNotEqual(self.connector.get('site', 'rule'), item)

    def test_item_separation(self):
        another = {1: 'one', 2: 'two', 3: 'three'}
        yetanother = {4: 'four', 5: 'five', 6: 'six'}
        self.connector.put('site', 'another', another)
        self.test_get_keymiss()
        self.test_new_item()
        self.assertEqual(self.connector.get('site', 'another'), another)
        self.connector.put('yet', 'another', yetanother)
        self.assertEqual(self.connector.get('site', 'another'), another)
        self.assertEqual(self.connector.get('yet', 'another'), yetanother)
        yetanother.update({7: 'seven'})
        self.connector.put('yet', 'another', yetanother)
        self.assertEqual(self.connector.get('site', 'another'), another)

    def test_remove_items(self):
        item1 = {'spam': 'eggs'}
        item2 = {'foo': 'bar'}
        self.connector.put('site', 'one', item1)
        self.connector.put('site', 'two', item2)
        self.assertEqual(self.connector.get('site', 'one'), item1)
        self.assertEqual(self.connector.get('site', 'two'), item2)
        self.connector.drop('site', 'one')
        self.assertEqual(self.connector.get('site', 'one'), {})
        self.assertEqual(self.connector.get('site', 'two'), item2)
        self.connector.put('site', 'one', item1)
        self.connector.drop('site')
        self.assertEqual(self.connector.get('site', 'one'), {})
        self.assertEqual(self.connector.get('site', 'two'), {})

    def test_list_items(self):
        site_results = []
        other_results = []

        self.connector.put('site', 'a', {})
        site_results.append(('site', 'a'))

        self.assertEqual(self.connector.list('site'), site_results)
        self.assertEqual(self.connector.list('site', 'a'), [('site', 'a')])

        self.connector.put('site', 'b', {})
        site_results.append(('site', 'b'))

        self.assertEqual(self.connector.list('site'), site_results)
        self.assertEqual(self.connector.list('site', 'a'), [('site', 'a')])
        self.assertEqual(self.connector.list('site', 'b'), [('site', 'b')])

        self.connector.put('other', 'a', {})
        other_results.append(('other', 'a'))
        self.assertEqual(self.connector.list('other', 'a'), other_results)
        self.assertEqual(self.connector.list('site'), site_results)

        self.assertEqual(self.connector.list(), site_results + other_results)

    def test_items_source(self):
        self.assertEqual(self.connector.source('site', 'one'), [])

        self.connector.put('site', 'one', {}, ['source.py'])
        self.assertEqual(self.connector.source('site', 'one'), ['source.py'])

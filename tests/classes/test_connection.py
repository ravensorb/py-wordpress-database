""" Tests for the WpConnection class. """

import unittest

from wpdatabase2.classes import WpCredentials
from wpdatabase2.classes import WpConnection

class ConnectionTestCase(unittest.TestCase):
    """ Tests for the WpConnection class. """

    def test_database_properties(self):
        """
        Assert that from_aws_secrets_manager() returns a class instance.
        """

        instance = WpConnection(db_host='127.0.0.1', db_name='wp_default', credentials=WpCredentials.from_username_and_password('root', 'password'))

        self.assertIsInstance(instance, WpConnection)
        self.assertEqual(instance.db_host, '127.0.0.1')
        self.assertIsInstance(instance.credentials, WpCredentials)
        self.assertEqual(instance.credentials.username, 'root')
        self.assertEqual(instance.credentials.password, 'password')

    def test_database_properties_db_host_none(self):
        """
        Assert that from_aws_secrets_manager() returns a class instance.
        """

        instance = WpConnection(db_host=None, db_name='wp_default', credentials=WpCredentials.from_username_and_password('root', 'password'))

        self.assertIsInstance(instance, WpConnection)
        self.assertIsNone(instance.db_host)
        self.assertIsInstance(instance.credentials, WpCredentials)
        self.assertEqual(instance.credentials.username, 'root')
        self.assertEqual(instance.credentials.password, 'password')

    def test_database_properties_credential_username_none(self):
        """
        Assert that from_aws_secrets_manager() returns a class instance.
        """

        instance = WpConnection(db_host=None, db_name='wp_default', credentials=WpCredentials.from_username_and_password(None, 'password'))

        self.assertIsInstance(instance, WpConnection)
        self.assertIsNone(instance.db_host)
        self.assertIsNone(instance.credentials)

if __name__ == '__main__':
    unittest.main()

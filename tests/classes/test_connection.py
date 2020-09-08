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

        self.assertTrue(isinstance(instance, WpConnection))
        self.assertTrue(instance.db_host is '127.0.0.1')
        self.assertTrue(isinstance(instance.credentials, WpCredentials))
        self.assertTrue(instance.credentials.username is 'root')
        self.assertTrue(instance.credentials.password is 'password')

if __name__ == '__main__':
    unittest.main()

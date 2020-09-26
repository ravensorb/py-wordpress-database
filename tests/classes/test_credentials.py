""" Tests for the WpCredentials class. """

import unittest

from wpdatabase2.classes import WpCredentials

class CredentialsTestCase(unittest.TestCase):
    """ Tests for the WpCredentials class. """

    def test_from_aws_secrets_manager(self):
        """
        Assert that from_aws_secrets_manager() returns a class instance.
        """

        instance = WpCredentials.from_aws_secrets_manager(
            secret_id='my-secret-id',
            region='my-region')

        self.assertTrue(isinstance(instance, WpCredentials))

    def test_from_username_and_password(self):
        """
        Assert that from_username_and_password() returns a class instance.
        """

        instance = WpCredentials.from_username_and_password(
            username='username',
            password='password')

        self.assertTrue(isinstance(instance, WpCredentials))
        self.assertEqual(instance.username, 'username', 'User name shoulld be "username"')
        self.assertEqual(instance.password, 'password', 'Password shoulld be "password"')

    def test_from_username_and_password_username_none(self):
        """
        Assert that from_username_and_password() returns a none if user name is None.
        """

        instance = WpCredentials.from_username_and_password(
            username=None,
            password='password')

        self.assertIsNone(instance)

    def test_from_username_and_password_password_none(self):
        """
        Assert that from_username_and_password() returns a none if password is None.
        """

        instance = WpCredentials.from_username_and_password(
            username='username',
            password=None)

        self.assertIsNone(instance)

if __name__ == '__main__':
    unittest.main()

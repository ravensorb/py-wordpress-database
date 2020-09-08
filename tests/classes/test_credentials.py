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


if __name__ == '__main__':
    unittest.main()

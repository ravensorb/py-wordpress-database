""" Tests for the Database class. """

import unittest
import json
import os

from wpdatabase2.classes import WpCredentials
from wpdatabase2.classes import WpConnection
from wpdatabase2.classes import WpDatabase

class DatabaseTestCase(unittest.TestCase):
    """ Tests for the Database class. """
    def _load_settings(self):
        cwd = os.getcwd()
        settingsFilePath = os.path.join(cwd, "tests", "test_settings.json")

        if not (os.path.exists(settingsFilePath)):
            return None

        with open(settingsFilePath) as f:
            dbSettings = json.load(f)

            return dbSettings

    def test_database_properties(self):
        """
        Assert that from_aws_secrets_manager() returns a class instance.
        """

        instance = WpDatabase(wp_connection=WpConnection(db_host='127.0.0.1:3306', db_name='wp_default', credentials=WpCredentials.from_username_and_password('root', 'password')))

        self.assertTrue(isinstance(instance, WpDatabase))
        self.assertTrue(isinstance(instance.connection, WpConnection))
        self.assertTrue(instance.connection.db_host == '127.0.0.1', 'Actual is: {0}'.format(instance.connection.db_host))
        self.assertTrue(instance.connection.db_port == '3306', 'Actual is: {0}'.format(instance.connection.db_port))
        self.assertTrue(instance.connection.db_name == 'wp_default', 'Actual is: {0}'.format(instance.connection.db_name))
        self.assertTrue(isinstance(instance.connection.credentials, WpCredentials))
        self.assertTrue(instance.connection.credentials.username is 'root')
        self.assertTrue(instance.connection.credentials.password is 'password')

    def test_database_connection(self):

        dbSettings = self._load_settings()
        self.assertTrue(dbSettings is not None, "test_settings.json must exist...")           

        instance = WpDatabase(wp_connection=WpConnection(
                                                        db_host=dbSettings["dbHost"], 
                                                        db_name=dbSettings["dbName"], 
                                                        credentials=WpCredentials.from_username_and_password(dbSettings["dbUser"], dbSettings["dbPassword"])))
        
        self.assertTrue(instance.test_config(), "Database connection failed")

    def test_get_database_version(self):

        dbSettings = self._load_settings()
        self.assertTrue(dbSettings is not None, "test_settings.json must exist...")           

        instance = WpDatabase(wp_connection=WpConnection(
                                                        db_host=dbSettings["dbHost"], 
                                                        db_name=dbSettings["dbName"], 
                                                        credentials=WpCredentials.from_username_and_password(dbSettings["dbUser"], dbSettings["dbPassword"])))

        wpVer = instance.get_database_version()
        self.assertTrue(wpVer is not None and wpVer.wp_version is not None, "Wordpress Version returned '{}'".format(wpVer))

if __name__ == '__main__':
    unittest.main()

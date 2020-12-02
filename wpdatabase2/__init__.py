"""
A Python package for creating and interacting with WordPress databases.
"""

import json
import logging

import boto3

from wpconfigr import WpConfigFile

from mysql import connector

from wpdatabase2.classes import Secret
from wpdatabase2.classes import WpCredentials
from wpdatabase2.classes import WpConnection
from wpdatabase2.classes import WpDatabase

from wpdatabase2.exceptions.invalid_arguments import InvalidArgumentsError # pylint: disable=line-too-long
from wpdatabase2.exceptions.invalid_database_name import InvalidDatabaseNameError # pylint: disable=line-too-long
from wpdatabase2.exceptions.region_not_known import RegionNotKnownError

def ensure(wp_config_filename, credentials, force = False):
    """
    Ensures that a WordPress database is set up according to the configuration
    in "wp-config.php".

    Args:
        wp_config_filename (str):  Path and filename of "wp-config.php".
        credentials (Credentials): Database admin user credentials.

    Raises:
        InvalidDatabaseNameError: The database name is invalid.
    """

    log = logging.getLogger(__name__)

    wp_config = WpConfigFile(filename=wp_config_filename)
    database = WpDatabase(wp_config=wp_config)

    log.info('Checking if the specified database has already been set up...')
    if database.test_config() and not force:
        log.info('Successfully connected.')
        return

    log.info('Could not connect, so will set up the database.')
    database.ensure_database_setup(admin_credentials=credentials, force=force)

    log.info('Validating the database setup...')
    if database.test_config(throw=True):
        log.info('Successfully connected.')

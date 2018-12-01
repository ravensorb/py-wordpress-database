"""
"wordpressdatabase" package initialization.
"""

import json
import logging

import boto3

from mysql.connector import connect

from wordpressdatabase.classes import Credentials
from wordpressdatabase.exceptions import UnhandledEngineError


def ensure(engine,
           host,
           admin_username=None,
           admin_password=None,
           admin_credentials_secret_id=None,
           db_name='wordpress',
           port=None,
           region=None):

    if engine != 'mysql':
        raise UnhandledEngineError()

    admin_credentials = Credentials(username=admin_username,
                                    password=admin_password,
                                    secret_id=admin_credentials_secret_id,
                                    region=region)

    conn = connect(
        host=host,
        user=admin_credentials.username,
        passwd=admin_credentials.password)

    cursor = conn.cursor()
    # Note that the parameter below needs to be a tuple, not a string.

    try:
        response = cursor.execute('CREATE DATABASE IF NOT EXISTS %s;', (db_name, ))
    except Exception as e:
        print(cursor.statement)
        raise e

    conn.commit()

    cursor.close()
    conn.close()

    print(str(response))


# def _get_credentials(secret_id,
#                      username_key='username',
#                      password_key='password'):

#     client = boto3.client('secretsmanager')
#     response = client.get_secret_value(SecretId=secret_id)
#     secret_string = response['SecretString']
#     secret = json.loads(secret_string)
#     return secret[username_key], secret[password_key]

""" Database connection details. """

from logging import getLogger
from wpdatabase2.classes import Secret
from wpdatabase2.classes import WpCredentials
from wpdatabase2.exceptions import InvalidArgumentsError

class WpConnection():
    """
    Represents a wordpress database connection details.

    Args:
        db_host (str):              database host.
        db_name (str):              database name.
        credentials (Credentials):  Database Credentials
    Raises:
        InvalidArgumentsError:         An invalid combination of arguments was
                                       passed to the constructor.
    """

    def __init__(self,
                 db_host,
                 db_name,
                 credentials):
        self._log = getLogger(__name__)

        if (not db_host):
            raise InvalidArgumentsError(
                'Must specify a database host/ip.')

        if (not db_name):
            raise InvalidArgumentsError(
                'Must specify a database name.')

        if (not credentials or not isinstance(credentials, WpCredentials)):
            raise InvalidArgumentsError(
                'Must specify a database credentials.')

        self.db_name = db_name
        self.db_host = db_host
        self.credentials = credentials

        self._log.debug('Host="%s", Port="%s", Name="%s"', self.db_host, self.db_port, self.db_name)

    ###########################################################################
    @property
    def db_host(self):
        """ Gets the database host. """
        return self._db_host

    ###########################################################################
    @db_host.setter
    def db_host(self, value):
        """ Gets the database host. """
        host_parts = value.split(':')
        self._db_host = host_parts[0]

        if len(host_parts) == 2:
            self._db_port = host_parts[1]
        else:
            self._db_port = None

    ###########################################################################
    @property
    def db_port(self):
        """ Gets the database port. """
        return self._db_port

    ###########################################################################
    @db_port.setter
    def db_port(self, value):
        """ Gets the database port. """
        self._db_port = value    

    ###########################################################################
    @property
    def db_name(self):
        """ Gets the database name. """
        return self._db_name

    ###########################################################################
    @db_name.setter
    def db_name(self, value):
        """ Sets the database name. """
        self._db_name = value    

    ###########################################################################
    @property
    def credentials(self):
        """ Gets the credentials. """
        return self._credentials

    ###########################################################################
    @credentials.setter
    def credentials(self, value):
        """ Sets the database credentials. """
        self._credentials = value    

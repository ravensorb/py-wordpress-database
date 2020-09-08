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

        self._db_name = db_name

        host_parts = db_host.split(':')
        self._db_host = host_parts[0]

        if len(host_parts) == 2:
            self._db_port = host_parts[1]
        else:
            self._db_port = None

        self._credentials = credentials

        self._log.debug('Host="%s", Port="%s", Name="%s"', self.db_host, self.db_port, self.db_name)

    @property
    def db_host(self):
        """ Gets the username. """
        return self._db_host

    @property
    def db_port(self):
        """ Gets the database port. """
        return self._db_port

    @property
    def db_name(self):
        """ Gets the database name. """
        return self._db_name

    @property
    def credentials(self):
        """ Gets the credentials. """
        return self._credentials

""" Common database functionality. """

# pylint: disable=line-too-long

from logging import getLogger
from wpconfigr import WpConfigFile
from mysql import connector
from wpdatabase2.classes.connection import WpConnection
from wpdatabase2.classes.credentials import WpCredentials
from wpdatabase2.exceptions import InvalidArgumentsError

class WpDatabase():
    """
    Database.

    Args:
        wp_config (wpconfigr.WpConfigFile): WordPress configuration.
        connection (Connection): WordPress configuration.
    """

    ###########################################################################
    def __init__(self, wp_config=None, wp_connection=None):
        """
        Constructor for Wpdatabase.ArithmeticError
        Note: Only wp_config OR wp_connection is required

        Args:
            wp_config (WpConfigFile, optional):     A WpConfigFile object
            connection (WpConnection, optional):    A WpConnection object
        """

        self._log = getLogger(__name__)

        if (wp_config is None and wp_connection is None):
            raise InvalidArgumentsError("Must specify at least one valid parameter (wp_config wp_connect)")

        if wp_config is not None:
            if not isinstance(wp_config, WpConfigFile):
                raise InvalidArgumentsError("wp_config must be an instance of WpConfigFile")

            self._wp_config = wp_config
            self._wp_connection = WpConnection(db_host=self._wp_config.get('DB_HOST'),
                                               db_name=self._wp_config.get('DB_NAME'),
                                               credentials=WpCredentials.from_username_and_password(self._wp_config.get('DB_USER'), self._wp_config.get('DB_PASSWORD')))
        elif wp_connection is not None:
            if not isinstance(wp_connection, WpConnection):
                raise InvalidArgumentsError("Invalid connection object")

            self._wp_connection = wp_connection

    ###########################################################################
    @property
    def connection(self):
        """ Gets the connection details. """
        return self._wp_connection

    ###########################################################################
    def _connect(self, credentials):
        """
        Gets a connection to the database.

        Args:
            credentials (Credentials): Database credentials.

        Returns:
            MySQLConnection: Database connection.
        """

        self._log.info('Attempting to connect...')

        if self._wp_connection.db_port:
            return connector.connect(host=self._wp_connection.db_host,
                                     port=self._wp_connection.db_port,
                                     user=credentials.username,
                                     password=credentials.password)

        return connector.connect(host=self._wp_connection.db_host,
                                 user=credentials.username,
                                 password=credentials.password)

    ###########################################################################
    def test_config(self, throw=False):
        """
        Tests the connection details in the WordPress configuration.

        Returns:
            bool: Success.
        """

        try:
            conn = self._connect(self._wp_connection.credentials)

            cur = conn.cursor()
            cur.execute("USE {}".format(self._wp_connection.db_name))

            cur.close()
            conn.close()

            return True

        except connector.errors.ProgrammingError as error:
            if throw:
                raise error
            return False

    ###########################################################################
    def does_database_exist(self):
        """
        Checks to see if the database exists

        Returns:
            bool: Success.
        """

        return self.test_config(False)

    ###########################################################################
    def get_database_version(self):
        """
        Returns the wordpress version (if it is configured)

        Returns:
            version (WpDatabaseVersion): Version details.
        """

        conn = self._connect(self._wp_connection.credentials)

        cur = conn.cursor()
        try:
            cur.execute("USE {}".format(self._wp_connection.db_name))
            cur.execute("SELECT option_value FROM `wp_options` where option_name = 'db_version'")
            record = cur.fetchone()
            cur.close()
            conn.close()

            if record is None:
                return None

            return WpDatabaseVersion(record[0])
        except connector.errors.ProgrammingError as error:
            self._log.error('Failed to execute: %s', cur.statement)
            raise error

    ###########################################################################
    def ensure_database_setup(self, admin_credentials):
        """
        Ensure the database is set up to match the WordPress configuration.

        Args:
            admin_credentials (Credentials): Database admin credentials.
        """

        def cur_exec(statement, params=None):
            sql = statement.format(n=self._wp_connection.db_name)
            try:
                cur.execute(sql, params)
            except connector.errors.ProgrammingError as error:
                self._log.error('Failed to execute: %s', cur.statement)
                raise error

        if self.does_database_exist():
            self._log.info('Database already "%s" exists...',
                           self._wp_connection.db_name)
            return

        conn = self._connect(admin_credentials)

        cur = conn.cursor()

        self._log.info('Ensuring database "%s" exists...', self._wp_connection.db_name)
        # Database names cannot be parameterized, so be careful.
        cur_exec('CREATE DATABASE IF NOT EXISTS {n};')
        #cur_exec('CREATE USER ''%s''@''*'' IDENTIFIED BY ''%s''', self._wp_connection.credentials.usernane, self._wp_connection.credentials.password)

        self._log.info('Using database "%s"...', self._wp_connection.db_name)
        cur_exec('USE {n};')

        self._log.info('Ensuring user "%s" exists...', self._wp_connection.credentials.username)
        cur_exec('GRANT ALL PRIVILEGES ON {n}.* TO %s@\'%\' IDENTIFIED BY %s;',
                 (self._wp_connection.credentials.username, self._wp_connection.credentials.password))

        self._log.info('Flushing privileges...')
        cur_exec('FLUSH PRIVILEGES;')

        self._log.info('Committing transaction...')
        conn.commit()

        self._log.info('Closing cursor...')
        cur.close()

        self._log.info('Closing connection...')
        conn.close()

        self._log.info('Database setup is complete.')

###########################################################################
###########################################################################

class WpDatabaseVersion():
    """ Database Version details """
    def __init__(self, ver):
        self._db_version = ver

    ###########################################################################
    @property
    def db_version(self):
        """ WordPress Raw Database Version Number """
        return self._db_version

    ###########################################################################
    @property
    def wp_version(self):
        """ WordPress Published Version Number """
        return self._wordPressVersions[self._db_version] if self._db_version in self._wordPressVersions else None

    ###########################################################################
    _wordPressVersions = {
        "2540" : "1.2.2",
        "2541" : "1.5.2",
        "3441" : "2.0.9",
        "4772" : "2.1.0",
        "4773" : "2.1.3",
        "5183" : "2.2.3",
        "6124" : "2.3.3",
        "7558" : "2.5.0",
        "7796" : "2.5.1",
        "8201" : "2.6.0",
        "8204" : "2.6.5",
        "9872" : "2.7.1",
        "11548" : "2.8.6",
        "12329" : "2.9.2",
        "15260" : "3.0.0",
        "15477" : "3.0.6",
        "17056" : "3.1.0",
        "17516" : "3.1.4",
        "18226" : "3.2.1",
        "19470" : "3.3.3",
        "20596" : "3.4.0",
        "21115" : "3.4.1",
        "21707" : "3.4.2",
        "22441" : "3.5.1",
        "22442" : "3.5.2",
        "24448" : "3.6.1",
        "25824" : "3.7.1",
        "26148" : "3.7.2",
        "26149" : "3.7.7",
        "26151" : "3.7.9",
        "26691" : "3.8.2",
        "26692" : "3.8.7",
        "26694" : "3.8.9",
        "27916" : "3.9.5",
        "27918" : "3.9.9",
        "29630" : "4.0.3",
        "29631" : "4.0.4",
        "29632" : "4.0.9",
        "30133" : "4.1.3",
        "30134" : "4.1.4",
        "30135" : "4.1.9",
        "31532" : "4.2.0",
        "31533" : "4.2.1",
        "31535" : "4.2.2",
        "31536" : "4.2.9",
        "33055" : "4.3.0",
        "33056" : "4.3.9",
        "35700" : "4.4.9",
        "36686" : "4.5.9",
        "37965" : "4.6.9",
        "38590" : "4.9.9",
        "43764" : "5.0.9",
        "44719" : "5.2.7",
        "45805" : "5.3.4",
        "47018" : "5.4.2",
        "48748" : "5.5.1",
    }

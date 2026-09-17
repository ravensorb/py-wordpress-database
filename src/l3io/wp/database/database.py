"""Inspecting and provisioning a WordPress database and its account.

Two design points are worth stating because the original got both wrong.

**The administrator is the authority on what exists.** Inspecting as the
WordPress account cannot answer "does this need provisioning?", because before
first provisioning that account does not exist and the inspection necessarily
fails. Refusing to provision on that failure would reject the most common case
this package serves -- a database made by ``wp db create`` or a container's
``MYSQL_DATABASE``, with no user yet.

**``wp-config.php`` is the desired state; the server is converged to it.** If
the configured password does not authenticate, it is reset. That direction is
declared rather than implied, and the reset only happens when it is needed, so
a run against an already-correct database performs no writes at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pymysql
import structlog
from opentelemetry import trace

from .connection import WpConnection
from .credentials import ResolvedCredentials, WpCredentials
from .errors import (
    AccessDeniedError,
    CredentialsUnobtainableError,
    DatabaseUnreachableError,
    ProvisioningError,
)
from .identifiers import quote_grant_database, quote_identifier, validate_user_name
from .state import ConnectionState
from .versions import WpDatabaseVersion

_log = structlog.get_logger(__name__)
_tracer = trace.get_tracer(__name__)

# Server error codes this module classifies on.
_ER_DBACCESS_DENIED = 1044
_ER_ACCESS_DENIED = 1045
_ER_BAD_DB = 1049

DEFAULT_CHARSET = "utf8mb4"
DEFAULT_COLLATION = "utf8mb4_unicode_ci"
DEFAULT_USER_HOST = "%"
CONNECT_TIMEOUT_SECONDS = 10


@dataclass(frozen=True, slots=True)
class EnsureResult:
    """What :meth:`WpDatabase.ensure` found and what it did about it."""

    state: ConnectionState
    changed: bool
    actions: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        """Whether the database is usable with the configured credentials."""
        return self.state.is_ready


class WpDatabase:
    """Operations against one WordPress database."""

    __slots__ = ("_connection",)

    def __init__(self, connection: WpConnection) -> None:
        self._connection = connection

    @property
    def connection(self) -> WpConnection:
        """The immutable descriptor this instance operates on."""
        return self._connection

    def inspect(self) -> ConnectionState:
        """Report why the database is or is not usable as configured.

        Never raises for an ordinary failure: the outcome *is* the return value.
        """
        try:
            resolved = self._connection.credentials.resolve()
        except CredentialsUnobtainableError:
            _log.info("credentials unobtainable", database=self._connection.database)
            return ConnectionState.CREDENTIALS_UNOBTAINABLE
        return self._probe(resolved)

    def exists(self) -> bool:
        """Whether the database is present and usable by the configured account.

        A narrow convenience over :meth:`inspect`. Prefer :meth:`inspect` when
        the reason matters -- which, before provisioning, it usually does.
        """
        return self.inspect().is_ready

    def database_version(self, table_prefix: str = "wp_") -> WpDatabaseVersion | None:
        """Read the WordPress schema revision from the site's options table.

        Args:
            table_prefix: WordPress's ``$table_prefix``. The original hardcoded
                ``wp_options``, so it failed on every site with a non-default
                prefix. Read the real value from
                :attr:`~l3io.wp.database.WpConfigSource.table_prefix`.

        Returns:
            The version, or ``None`` when the options table holds no
            ``db_version`` row.

        Raises:
            AccessDeniedError: the options table could not be read.
            DatabaseUnreachableError: the server could not be reached.
        """
        options = quote_identifier(f"{table_prefix}options")
        resolved = self._connection.credentials.resolve()
        try:
            connection = self._raw_connect(resolved, database=self._connection.database)
        except pymysql.err.MySQLError as exc:
            msg = f"could not connect to read {options}"
            raise DatabaseUnreachableError(msg) from exc

        try:
            with connection, connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT option_value FROM {options} WHERE option_name = %s",  # noqa: S608 - quoted identifier
                    ("db_version",),
                )
                row = cursor.fetchone()
        except pymysql.err.MySQLError as exc:
            msg = f"could not read {options}; is the table prefix {table_prefix!r} correct?"
            raise AccessDeniedError(msg) from exc

        if row is None or row[0] is None:
            return None
        try:
            return WpDatabaseVersion(int(row[0]))
        except (TypeError, ValueError) as exc:
            msg = f"db_version {row[0]!r} in {options} is not an integer"
            raise AccessDeniedError(msg) from exc

    def ensure(
        self,
        admin_credentials: WpCredentials,
        *,
        force: bool = False,
        user_host: str = DEFAULT_USER_HOST,
        charset: str = DEFAULT_CHARSET,
        collation: str = DEFAULT_COLLATION,
    ) -> EnsureResult:
        """Converge the server onto the configured database and account.

        Args:
            admin_credentials: an account permitted to create databases and
                users. Required -- this is never defaulted to the WordPress
                account, which would be privilege escalation by accident.
            force: provision even when the database is already usable.
            user_host: host part of the account to grant, ``'%'`` by default.
            charset: character set for a newly created database.
            collation: collation for a newly created database.

        Returns:
            EnsureResult: the final state, whether anything changed, and what
            was done.

        Raises:
            DatabaseUnreachableError: the server could not be reached, so
                nothing can be concluded about what exists.
            CredentialsUnobtainableError: either credential source failed.
            ProvisioningError: a statement failed, or the database was still
                not usable afterwards.
        """
        with _tracer.start_as_current_span("l3io.wp.database.ensure") as span:
            span.set_attribute("db.name", self._connection.database)
            span.set_attribute("server.address", self._connection.host)
            span.set_attribute("server.port", self._connection.port)

            initial = self.inspect()
            span.set_attribute("l3io.initial_state", str(initial))

            if initial.blocks_provisioning:
                if initial is ConnectionState.CREDENTIALS_UNOBTAINABLE:
                    msg = "the WordPress credentials could not be obtained"
                    raise CredentialsUnobtainableError(msg)
                msg = (
                    f"{self._connection.host}:{self._connection.port} could not be "
                    "reached, so nothing can be created on the strength of it"
                )
                raise DatabaseUnreachableError(msg)

            if initial.is_ready and not force:
                _log.info(
                    "already provisioned",
                    database=self._connection.database,
                    state=str(initial),
                )
                span.set_attribute("l3io.changed", False)
                return EnsureResult(state=initial, changed=False)

            admin = admin_credentials.resolve()
            wordpress = self._connection.credentials.resolve()
            actions = self._provision(
                admin=admin,
                wordpress=wordpress,
                reset_password=force or initial is not ConnectionState.READY,
                user_host=user_host,
                charset=charset,
                collation=collation,
            )

            final = self.inspect()
            span.set_attribute("l3io.final_state", str(final))
            span.set_attribute("l3io.changed", bool(actions))

            if not final.is_ready:
                msg = (
                    f"provisioning ran but {self._connection.database!r} is still not "
                    f"usable by {wordpress.username!r}: {final}"
                )
                raise ProvisioningError(msg)

            _log.info(
                "provisioned",
                database=self._connection.database,
                actions=list(actions),
                state=str(final),
            )
            return EnsureResult(state=final, changed=bool(actions), actions=actions)

    def _provision(
        self,
        *,
        admin: ResolvedCredentials,
        wordpress: ResolvedCredentials,
        reset_password: bool,
        user_host: str,
        charset: str,
        collation: str,
    ) -> tuple[str, ...]:
        database = self._connection.database
        username = validate_user_name(wordpress.username)
        actions: list[str] = []

        # Identifiers cannot be parameterized, so they are validated and quoted.
        # The GRANT clause is matched as a LIKE pattern, so its database name is
        # additionally wildcard-escaped -- see identifiers.quote_grant_database.
        quoted_db = quote_identifier(database)
        grant_db = quote_grant_database(database)

        try:
            connection = self._raw_connect(admin, database=None)
        except pymysql.err.MySQLError as exc:
            msg = f"could not connect as the administrator to provision {database!r}"
            raise ProvisioningError(msg) from exc

        try:
            with connection, connection.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS {quoted_db} "  # noqa: S608 - quoted identifier
                    f"CHARACTER SET {charset} COLLATE {collation}"
                )
                actions.append(f"create database {database}")

                cursor.execute(
                    "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                    (username, user_host, wordpress.password),
                )
                actions.append(f"create user {username}@{user_host}")

                if reset_password:
                    # CREATE USER IF NOT EXISTS leaves an existing account's
                    # password untouched, so converging onto wp-config.php
                    # requires ALTER USER. Skipped when the account already
                    # authenticates, so an idempotent run performs no writes.
                    cursor.execute(
                        "ALTER USER %s@%s IDENTIFIED BY %s",
                        (username, user_host, wordpress.password),
                    )
                    actions.append(f"set password for {username}@{user_host}")

                cursor.execute(
                    f"GRANT ALL PRIVILEGES ON {grant_db}.* TO %s@%s"  # noqa: S608 - escaped identifier
                    "",
                    (username, user_host),
                )
                actions.append(f"grant on {database} to {username}@{user_host}")

                cursor.execute("FLUSH PRIVILEGES")
                connection.commit()
        except pymysql.err.MySQLError as exc:
            msg = f"provisioning {database!r} failed after {len(actions)} statement(s)"
            raise ProvisioningError(msg) from exc

        return tuple(actions)

    def _probe(self, credentials: ResolvedCredentials) -> ConnectionState:
        try:
            connection = self._raw_connect(credentials, database=self._connection.database)
        except pymysql.err.OperationalError as exc:
            code = exc.args[0] if exc.args else None
            if code == _ER_ACCESS_DENIED:
                return ConnectionState.AUTHENTICATION_FAILED
            if code == _ER_DBACCESS_DENIED:
                return ConnectionState.ACCESS_DENIED
            if code == _ER_BAD_DB:
                return ConnectionState.DATABASE_ABSENT
            return ConnectionState.UNREACHABLE
        except pymysql.err.MySQLError:
            return ConnectionState.UNREACHABLE

        connection.close()
        return ConnectionState.READY

    def _raw_connect(
        self, credentials: ResolvedCredentials, *, database: str | None
    ) -> pymysql.connections.Connection:
        """Open a connection. Credentials go as arguments, never in a URI."""
        return pymysql.connect(
            host=self._connection.host,
            port=self._connection.port,
            user=credentials.username,
            password=credentials.password,
            database=database,
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
        )

"""Exception hierarchy owned by this package.

AD-14: no dependency's exception type crosses a public boundary. Driver and SDK
errors are caught and re-raised as one of these, with ``raise ... from``.
"""

from __future__ import annotations


class WpDatabaseError(Exception):
    """Base class for every error this package raises."""


class InvalidArgumentsError(WpDatabaseError):
    """An invalid combination of arguments was supplied."""


class InvalidIdentifierError(WpDatabaseError):
    """A database or user name is not usable as a MySQL identifier."""

    def __init__(self, kind: str, value: str, reason: str) -> None:
        self.kind = kind
        self.value = value
        self.reason = reason
        super().__init__(f"{kind} {value!r} is not a valid identifier: {reason}")


class InvalidDatabaseNameError(InvalidIdentifierError):
    """A database name is not usable as a MySQL identifier."""

    def __init__(self, value: str, reason: str = "not a valid database name") -> None:
        super().__init__("database name", value, reason)


class MissingDependencyError(WpDatabaseError):
    """An optional feature was used without its extra installed.

    AD-8: optional dependencies are imported inside the function that needs
    them, and their absence is reported by naming the extra to install.
    """

    def __init__(self, extra: str, distribution: str) -> None:
        self.extra = extra
        self.distribution = distribution
        super().__init__(
            f"this feature needs {distribution!r}, which is not installed. "
            f"Install it with: pip install 'l3io-wp-database[{extra}]'"
        )


class CredentialsUnobtainableError(WpDatabaseError):
    """Credentials could not be obtained from their source.

    Distinct from authentication failure: nothing was attempted against the
    database, because there was nothing to attempt it with.
    """


class RegionNotKnownError(CredentialsUnobtainableError):
    """An AWS region was neither supplied nor discoverable from the session."""

    def __init__(self) -> None:
        super().__init__(
            "the AWS region was not supplied and could not be determined from the current session"
        )


class ConfigurationError(WpDatabaseError):
    """A WordPress configuration file could not be used."""


class ConfigUnreadableError(ConfigurationError):
    """The configuration file could not be read."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        super().__init__(f"could not read WordPress configuration {path!r}: {reason}")


class MissingConfigValueError(ConfigurationError):
    """A setting the database needs is not defined in the configuration."""

    def __init__(self, key: str, path: str) -> None:
        self.key = key
        self.path = path
        super().__init__(f"{key} is not defined in {path!r}")


class DatabaseUnreachableError(WpDatabaseError):
    """The database server could not be reached at all."""


class AuthenticationFailedError(WpDatabaseError):
    """The server was reached but rejected the supplied credentials."""


class AccessDeniedError(WpDatabaseError):
    """Authentication succeeded but the account may not use the database."""


class ProvisioningError(WpDatabaseError):
    """A provisioning statement failed."""

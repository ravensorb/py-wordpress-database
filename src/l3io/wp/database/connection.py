"""Where a WordPress database lives and who connects to it.

AD-3: one immutable site descriptor. The original had two writers for a single
value -- ``db_host``'s setter parsed ``host:port`` and derived ``_db_port``,
while ``db_port`` had its own independent setter, so assigning ``db_host``
after ``db_port`` silently discarded the port. Parsed once, frozen, no setters.
"""

from __future__ import annotations

from dataclasses import dataclass

from .credentials import WpCredentials
from .errors import InvalidArgumentsError
from .identifiers import validate_database_name

DEFAULT_PORT = 3306


@dataclass(frozen=True, slots=True)
class WpConnection:
    """An immutable description of one WordPress database and its account."""

    host: str
    database: str
    credentials: WpCredentials
    port: int = DEFAULT_PORT

    def __post_init__(self) -> None:
        if not self.host:
            msg = "host must not be empty"
            raise InvalidArgumentsError(msg)
        if not isinstance(self.port, int) or not (0 < self.port < 65536):
            msg = f"port must be an integer between 1 and 65535, not {self.port!r}"
            raise InvalidArgumentsError(msg)
        validate_database_name(self.database)

    @classmethod
    def from_db_host(cls, db_host: str, db_name: str, credentials: WpCredentials) -> WpConnection:
        """Build from WordPress's ``DB_HOST``, which may carry ``host:port``.

        This is the only place the combined form is parsed.
        """
        if not db_host:
            msg = "DB_HOST must not be empty"
            raise InvalidArgumentsError(msg)

        host, separator, port_text = db_host.partition(":")
        if separator and port_text:
            try:
                port = int(port_text)
            except ValueError as exc:
                msg = f"DB_HOST port {port_text!r} is not an integer"
                raise InvalidArgumentsError(msg) from exc
        else:
            port = DEFAULT_PORT

        return cls(host=host, database=db_name, credentials=credentials, port=port)

    def __repr__(self) -> str:
        return (
            f"WpConnection(host={self.host!r}, port={self.port}, "
            f"database={self.database!r}, credentials={self.credentials!r})"
        )

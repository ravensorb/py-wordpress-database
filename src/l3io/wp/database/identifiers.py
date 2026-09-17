"""Validating and quoting MySQL identifiers.

This module exists because of a verified privilege-escalation defect in the
original package. A *database-level* ``GRANT`` treats the database name as a
``LIKE`` pattern, so ``_`` is a single-character wildcard. Granting on
``wp_site`` therefore also grants on ``wpXsite``:

    GRANT ALL PRIVILEGES ON `wp_site`.* TO 'victim'@'%';
    -- victim can then SHOW and CREATE TABLE in wpXsite

Backticks do not suppress this; only escaping the wildcard does. Because
essentially every WordPress database is named with an underscore, the original
``GRANT ALL PRIVILEGES ON {n}.*`` over-granted every user it created.
"""

from __future__ import annotations

from .errors import InvalidDatabaseNameError, InvalidIdentifierError

#: MySQL caps database names at 64 characters. MariaDB allows longer user names
#: than MySQL's 32, so the stricter MySQL limit is applied to both.
MAX_DATABASE_NAME = 64
MAX_USER_NAME = 32

_FORBIDDEN = {"\x00", "\n", "\r", "`", "/", "\\", "."}


def _check(kind: str, value: str, limit: int) -> None:
    if not isinstance(value, str) or not value:
        raise InvalidIdentifierError(kind, str(value), "must be a non-empty string")
    if len(value) > limit:
        raise InvalidIdentifierError(kind, value, f"longer than {limit} characters")
    if value != value.strip():
        raise InvalidIdentifierError(kind, value, "has leading or trailing whitespace")
    found = _FORBIDDEN.intersection(value)
    if found:
        chars = ", ".join(repr(c) for c in sorted(found))
        raise InvalidIdentifierError(kind, value, f"contains forbidden characters: {chars}")


def validate_database_name(name: str) -> str:
    """Return ``name`` if it is usable as a database identifier, else raise."""
    try:
        _check("database name", name, MAX_DATABASE_NAME)
    except InvalidIdentifierError as exc:
        raise InvalidDatabaseNameError(str(name), exc.reason) from exc
    return name


def validate_user_name(name: str) -> str:
    """Return ``name`` if it is usable as a user identifier, else raise."""
    _check("user name", name, MAX_USER_NAME)
    return name


def quote_identifier(name: str) -> str:
    """Backtick-quote an identifier, doubling any internal backticks."""
    return "`" + name.replace("`", "``") + "`"


def quote_grant_database(name: str) -> str:
    """Quote a database name for the ``ON <db>.*`` clause of a GRANT.

    The clause is matched as a ``LIKE`` pattern, so ``_`` and ``%`` must be
    escaped or the grant silently widens to every database matching the
    pattern. This is the fix for the defect described in the module docstring.
    """
    escaped = name.replace("\\", "\\\\").replace("_", r"\_").replace("%", r"\%")
    return quote_identifier(escaped)

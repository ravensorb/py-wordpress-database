"""AD-3: the site descriptor is parsed once and frozen."""

from __future__ import annotations

import dataclasses

import pytest

from l3io.wp.database import DEFAULT_PORT, WpConnection, WpCredentials
from l3io.wp.database.errors import InvalidArgumentsError, InvalidDatabaseNameError


def creds() -> WpCredentials:
    return WpCredentials.from_username_and_password("wp", "pw")


def test_db_host_with_port_is_split() -> None:
    c = WpConnection.from_db_host("127.0.0.1:3307", "wp_site", creds())
    assert (c.host, c.port) == ("127.0.0.1", 3307)


def test_db_host_without_port_defaults() -> None:
    c = WpConnection.from_db_host("db.internal", "wp_site", creds())
    assert (c.host, c.port) == ("db.internal", DEFAULT_PORT)


def test_the_descriptor_is_frozen() -> None:
    """The original let db_host's setter silently discard an assigned db_port."""
    c = WpConnection.from_db_host("127.0.0.1:3307", "wp_site", creds())
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.host = "elsewhere"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.port = 1234  # type: ignore[misc]


def test_non_numeric_port_is_rejected_at_construction() -> None:
    with pytest.raises(InvalidArgumentsError):
        WpConnection.from_db_host("127.0.0.1:not-a-port", "wp_site", creds())


def test_out_of_range_port_is_rejected() -> None:
    with pytest.raises(InvalidArgumentsError):
        WpConnection(host="h", database="wp", credentials=creds(), port=70000)


def test_database_name_is_validated_at_construction() -> None:
    with pytest.raises(InvalidDatabaseNameError):
        WpConnection.from_db_host("127.0.0.1", "bad.name", creds())


def test_repr_does_not_leak_the_password() -> None:
    c = WpConnection.from_db_host("127.0.0.1", "wp_site", creds())
    assert "pw" not in repr(c)

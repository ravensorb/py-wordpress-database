"""AD-9: resolution is an explicit call, not a property read."""

from __future__ import annotations

import pytest

from l3io.wp.database import ResolvedCredentials, WpCredentials
from l3io.wp.database.errors import InvalidArgumentsError


def test_explicit_pair_resolves() -> None:
    r = WpCredentials.from_username_and_password("wp", "pw").resolve()
    assert r == ResolvedCredentials("wp", "pw")


def test_partial_input_raises_instead_of_returning_none() -> None:
    """The original returned None here; three commits chased the fallout."""
    with pytest.raises(InvalidArgumentsError):
        WpCredentials.from_username_and_password("wp", None)  # type: ignore[arg-type]
    with pytest.raises(InvalidArgumentsError):
        WpCredentials.from_username_and_password(None, "pw")  # type: ignore[arg-type]


def test_both_sources_at_once_is_rejected() -> None:
    with pytest.raises(InvalidArgumentsError):
        WpCredentials(username="wp", password="pw", aws_secret_id="sid")


def test_no_source_at_all_is_rejected() -> None:
    with pytest.raises(InvalidArgumentsError):
        WpCredentials()


def test_there_are_no_resolving_property_getters() -> None:
    """Attribute access must not perform I/O; that was the AD-9 defect."""
    c = WpCredentials.from_aws_secrets_manager("sid", "us-east-1")
    assert not hasattr(c, "username")
    assert not hasattr(c, "password")


def test_resolved_password_is_redacted_in_repr() -> None:
    r = ResolvedCredentials("wp", "super-secret")
    assert "super-secret" not in repr(r)
    assert "wp" in repr(r)


def test_source_is_reportable_without_leaking_anything() -> None:
    assert WpCredentials.from_username_and_password("wp", "pw").source == "explicit"
    assert WpCredentials.from_aws_secrets_manager("sid").source == "aws-secrets-manager"
    assert "sid" not in repr(WpCredentials.from_aws_secrets_manager("sid"))

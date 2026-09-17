"""The command line interface, and its exit-code contract.

Distinct exit codes per failure class are the point: the state model exists so
that "could not connect" and "database absent" are different answers, and
automation should be able to branch on them without parsing messages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from l3io.wp.database.cli import Exit, main


def test_version_exits_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--version"])
    assert caught.value.code == 0
    assert "1.0.0" in capsys.readouterr().out


def test_no_source_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--admin-username", "root", "--admin-password", "pw"])
    assert caught.value.code == Exit.USAGE


def test_partial_explicit_source_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--db-host", "127.0.0.1", "--db-name", "wp"])
    assert caught.value.code == Exit.USAGE


def test_both_sources_is_a_usage_error(tmp_path: Path) -> None:
    config = tmp_path / "wp-config.php"
    config.write_text("<?php\n")
    with pytest.raises(SystemExit) as caught:
        main(["--wp-config", str(config), "--db-host", "127.0.0.1"])
    assert caught.value.code == Exit.USAGE


def test_missing_admin_credentials_is_a_usage_error() -> None:
    """Administrative credentials are never defaulted to the WordPress account."""
    with pytest.raises(SystemExit) as caught:
        main(
            [
                "--db-host",
                "127.0.0.1:1",
                "--db-name",
                "wp_site",
                "--db-user",
                "wp",
                "--db-password",
                "pw",
            ]
        )
    assert caught.value.code == Exit.USAGE


def test_both_admin_sources_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as caught:
        main(
            [
                "--db-host",
                "127.0.0.1:1",
                "--db-name",
                "wp_site",
                "--db-user",
                "wp",
                "--db-password",
                "pw",
                "--admin-username",
                "root",
                "--admin-password",
                "pw",
                "--admin-credentials-aws-secret-id",
                "sid",
            ]
        )
    assert caught.value.code == Exit.USAGE


def test_inspect_reports_state_and_does_not_need_admin_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--inspect changes nothing, so it requires no administrative credentials."""
    code = main(
        [
            "--inspect",
            "--db-host",
            "127.0.0.1:1",
            "--db-name",
            "wp_site",
            "--db-user",
            "wp",
            "--db-password",
            "pw",
        ]
    )
    assert code == Exit.NOT_READY
    assert capsys.readouterr().out.strip() == "unreachable"


def test_unreachable_server_exits_with_its_own_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Not a generic failure: nothing may be created on an unreachable server."""
    code = main(
        [
            "--db-host",
            "127.0.0.1:1",
            "--db-name",
            "wp_site",
            "--db-user",
            "wp",
            "--db-password",
            "pw",
            "--admin-username",
            "root",
            "--admin-password",
            "pw",
        ]
    )
    assert code == Exit.UNREACHABLE
    assert "could not be reached" in capsys.readouterr().err


def test_invalid_database_name_is_reported_not_interpolated(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        [
            "--inspect",
            "--db-host",
            "127.0.0.1:1",
            "--db-name",
            "bad.name",
            "--db-user",
            "wp",
            "--db-password",
            "pw",
        ]
    )
    assert code == Exit.USAGE
    assert "not a valid" in capsys.readouterr().err


def test_a_missing_wp_config_reports_our_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code = main(["--inspect", "--wp-config", str(tmp_path / "absent.php")])
    assert code == Exit.CONFIGURATION
    assert "could not read" in capsys.readouterr().err

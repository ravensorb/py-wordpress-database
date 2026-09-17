"""The wp-config.php adapter.

Skipped when the `wpconfig` extra is absent, which is the point of the extra.
Each test names the upstream behaviour it guards, because all three changed in
l3io-wp-config 1.5.0 and a direct port of the old call sites would be wrong.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from l3io.wp.database import DEFAULT_TABLE_PREFIX, WpConfigSource
from l3io.wp.database.errors import ConfigUnreadableError, MissingConfigValueError

pytest.importorskip("l3io.wp.config", reason="the wpconfig extra is not installed")

CONFIG = """<?php
define('DB_NAME', 'wp_site');
define('DB_USER', 'wpuser');
define('DB_PASSWORD', 'wp-pass');
define('DB_HOST', '127.0.0.1:3307');
$table_prefix = 'custom_';
"""


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "wp-config.php"
    path.write_text(body)
    return path


def test_connection_is_built_from_the_configuration(tmp_path: Path) -> None:
    source = WpConfigSource(write(tmp_path, CONFIG))
    conn = source.connection()
    assert (conn.host, conn.port, conn.database) == ("127.0.0.1", 3307, "wp_site")
    assert conn.credentials.resolve().username == "wpuser"


def test_table_prefix_comes_from_the_variable_namespace(tmp_path: Path) -> None:
    """$table_prefix is a PHP variable, so get() cannot see it."""
    source = WpConfigSource(write(tmp_path, CONFIG))
    assert source.table_prefix == "custom_"


def test_table_prefix_falls_back_to_the_wordpress_default(tmp_path: Path) -> None:
    body = CONFIG.replace("$table_prefix = 'custom_';\n", "")
    assert WpConfigSource(write(tmp_path, body)).table_prefix == DEFAULT_TABLE_PREFIX


def test_a_missing_setting_names_itself(tmp_path: Path) -> None:
    body = CONFIG.replace("define('DB_HOST', '127.0.0.1:3307');\n", "")
    source = WpConfigSource(write(tmp_path, body))
    with pytest.raises(MissingConfigValueError) as caught:
        source.connection()
    assert caught.value.key == "DB_HOST"


def test_an_empty_setting_is_present_not_absent(tmp_path: Path) -> None:
    """The falsiness trap: MISSING is falsy, and so is an empty string.

    A truthiness test cannot tell them apart. An empty password is a real
    configured value -- unwise, but configured, and MySQL permits it -- so it
    must travel through as an empty string rather than being reported as
    undefined. Conflating empty with absent is the confusion this rewrite
    exists to remove, so it is asserted at both layers: the config read does
    not raise MissingConfigValueError, and the credential type accepts it
    because it tests `is None` rather than falsiness.
    """
    body = CONFIG.replace("define('DB_PASSWORD', 'wp-pass');", "define('DB_PASSWORD', '');")
    source = WpConfigSource(write(tmp_path, body))
    resolved = source.connection().credentials.resolve()
    assert resolved.password == ""
    assert resolved.username == "wpuser"


def test_a_quoted_numeric_password_stays_text(tmp_path: Path) -> None:
    """Upstream used to coerce quoted numerics to float, so '3306' became 3306.0."""
    body = CONFIG.replace("define('DB_PASSWORD', 'wp-pass');", "define('DB_PASSWORD', '3306');")
    source = WpConfigSource(write(tmp_path, body))
    resolved = source.connection().credentials.resolve()
    assert resolved.password == "3306"
    assert isinstance(resolved.password, str)


def test_an_unreadable_file_raises_our_error_not_the_stdlib_one(tmp_path: Path) -> None:
    """AD-14 -- no dependency's exception type crosses this boundary."""
    with pytest.raises(ConfigUnreadableError):
        WpConfigSource(tmp_path / "does-not-exist.php")

# Changelog

## 1.0.0 — unreleased

A full internal rewrite. The package is renamed, re-namespaced, and its
behaviour corrected. Nothing is preserved from the `wpdatabase2` public API;
see [Migrating](#migrating-from-wpdatabase2).

### Renamed

- Distribution `wpdatabase2` becomes **`l3io-wp-database`**; import path
  `wpdatabase2` becomes **`l3io.wp.database`**, a PEP 420 namespace shared with
  `l3io-wp-config` and `l3io-wp-backup`.
- No compatibility shim is published. No release of `wpdatabase2` was ever
  installable from PyPI — every published version pinned a distribution that no
  longer exists, so `pip install wpdatabase2` failed with `ResolutionImpossible`
  for roughly six years. A shim would protect an audience that cannot exist
  through pip.

### Fixed

- **`test_config()` always returned `False`.** `with self._connect(...) as conn`
  raised `TypeError: 'MySQLConnection' object does not support the context
  manager protocol` under the pinned driver, and a bare `except Exception`
  swallowed it. So `does_database_exist()` was always `False`, `ensure()` always
  ran the administrative path, and its closing validation always raised.
- **Grants over-granted.** A database-level `GRANT` matches its target as a
  `LIKE` pattern, so `_` is a single-character wildcard: a grant on `wp_site`
  also covered `wpXsite`. Since nearly every WordPress database name contains an
  underscore, every user this package created was over-granted. Wildcards in a
  grant target are now escaped, with a test asserting the neighbouring database
  is *unreachable*.
- **Existence could not be distinguished from failure.** Every error was
  reported as "not found", so an authentication failure or an unreachable host
  looked identical to a missing database — and the next step was to create
  objects with administrative credentials. `inspect()` now reports six distinct
  states.
- **`InvalidDatabaseNameError` was documented as raised but never raised**, and
  database names reached SQL through unvalidated string interpolation.
  Identifiers are now validated, quoted and escaped.
- **`get_database_version()` hardcoded `wp_options`**, so it failed on any site
  with a non-default `$table_prefix`.
- **User creation used `GRANT ... IDENTIFIED BY`**, removed in MySQL 8.0 and a
  syntax error there. Now `CREATE USER IF NOT EXISTS`, then `ALTER USER` to
  converge the password, then `GRANT` without `IDENTIFIED BY`.

### Changed

- **Driver:** `mysql-connector` 2.2.9 (last released 2019, and deprecated by its
  own PyPI page) replaced with `PyMySQL[rsa]`.
- **Credential resolution is an explicit call.** `WpCredentials.username` and
  `.password` were property *getters* that performed an AWS round trip and
  mutated `self`. Use `resolve()`, which returns a frozen value.
- **The connection descriptor is immutable.** `db_host`'s setter parsed
  `host:port` while `db_port` had its own setter, so the two could desync and
  assigning `db_host` last silently discarded the port. Parsed once at
  construction; no setters.
- **Partial credentials raise.** `from_username_and_password()` returned `None`
  when given only one of username or password, which surfaced later as an
  `AttributeError`. It now raises `InvalidArgumentsError`. An *empty* password is
  still accepted: MySQL permits it, and empty is not absent.
- **No dependency's exception type crosses the public boundary.** Driver, AWS
  and config-reader errors are re-raised as this package's own types.
- **Optional dependencies are optional imports.** `boto3` and the config reader
  are imported inside the code that uses them, so a base install imports
  neither.
- **Observability:** structured logging via `structlog`, and OpenTelemetry spans
  around `ensure()` and the operations it performs. No credential, secret value
  or secret identifier is logged.
- **Packaging:** `pyproject.toml` with a committed `uv.lock`, replacing
  `setup.py`, `setup.cfg`, `build.sh`, `publish.sh` and `test.py`. Python 3.11+.
  `py.typed` shipped.
- **Supported servers:** MySQL 8.0, 8.4, 9.x and MariaDB 10.2+. MySQL 5.7 is no
  longer supported.

### Not changed, contrary to an upstream note

An upstream handoff recorded that this package "silently reuses the ordinary
database credentials for `CREATE DATABASE` and `GRANT` when no administrative
credentials are supplied". No such code path existed here:
`ensure_database_setup` took administrative credentials as a required parameter
and passed them straight to the connection, and the CLI exited non-zero when
neither source was given. The defect was in a sibling package. It is recorded
here only because the handoff asked for a changelog entry, and describing a
change that did not happen would be worse than saying so.

## Migrating from `wpdatabase2`

| Before | After |
|---|---|
| `import wpdatabase2` | `from l3io.wp import database` |
| `wpdatabase2.ensure(path, credentials)` | `WpDatabase(WpConfigSource(path).connection()).ensure(admin)` |
| `WpConnection(db_host=..., db_name=...)` | `WpConnection.from_db_host(db_host=..., db_name=...)` |
| `credentials.username` | `credentials.resolve().username` |
| `db.test_config()` | `db.inspect().is_ready` |
| `db.does_database_exist()` | `db.inspect()` — six states, not a boolean |
| `except mysql.connector.Error` | `except WpDatabaseError` |

"""Command line entry point.

The library never configures logging; this does, because it owns the process.

Exit codes are distinct per failure class so that automation can branch on
them without parsing messages -- the whole point of the state model is that
"could not connect" and "database absent" are different answers.
"""

from __future__ import annotations

import argparse
import logging
import sys
from enum import IntEnum
from typing import NoReturn

import structlog

from ._version import __version__
from .connection import WpConnection
from .credentials import WpCredentials
from .database import WpDatabase
from .errors import (
    ConfigurationError,
    CredentialsUnobtainableError,
    DatabaseUnreachableError,
    InvalidArgumentsError,
    InvalidIdentifierError,
    MissingDependencyError,
    ProvisioningError,
)
from .state import ConnectionState


class Exit(IntEnum):
    """Process exit codes."""

    OK = 0
    FAILED = 1
    USAGE = 2
    CONFIGURATION = 3
    CREDENTIALS = 4
    UNREACHABLE = 5
    PROVISIONING = 6
    NOT_READY = 7


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="l3io-wp-database",
        description=("Create and inspect WordPress MySQL databases and their users, idempotently."),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="report the database's state and exit without changing anything",
    )
    parser.add_argument("--force", action="store_true", help="provision even if already usable")
    parser.add_argument("--log-level", default="INFO", help="logging level (default: INFO)")

    source = parser.add_argument_group("where the WordPress settings come from")
    source.add_argument(
        "--wp-config",
        help="path to wp-config.php (needs the 'wpconfig' extra)",
    )
    source.add_argument("--db-host", help="database host, optionally host:port")
    source.add_argument("--db-name", help="database name")
    source.add_argument("--db-user", help="WordPress database user")
    source.add_argument("--db-password", help="WordPress database password")

    admin = parser.add_argument_group("administrative credentials, required to provision")
    admin.add_argument("--admin-username", help="administrative username")
    admin.add_argument("--admin-password", help="administrative password")
    admin.add_argument(
        "--admin-credentials-aws-secret-id",
        help="AWS Secrets Manager secret id holding the admin credentials (needs the 'aws' extra)",
    )
    admin.add_argument(
        "--admin-credentials-aws-region",
        help="AWS region the secret resides in",
    )
    return parser


def _fail(parser: argparse.ArgumentParser, message: str) -> NoReturn:
    parser.error(message)  # exits with Exit.USAGE


def resolve_connection(args: argparse.Namespace, parser: argparse.ArgumentParser) -> WpConnection:
    """Build the connection descriptor from whichever source was given."""
    explicit = (args.db_host, args.db_name, args.db_user, args.db_password)
    if args.wp_config and any(explicit):
        _fail(parser, "give either --wp-config or the explicit --db-* options, not both")

    if args.wp_config:
        # Imported here so the CLI starts without the wpconfig extra installed.
        from .wpconfig import WpConfigSource

        return WpConfigSource(args.wp_config).connection()

    if not all(explicit):
        _fail(
            parser,
            "give --wp-config, or all of --db-host, --db-name, --db-user and --db-password",
        )
    return WpConnection.from_db_host(
        db_host=args.db_host,
        db_name=args.db_name,
        credentials=WpCredentials.from_username_and_password(args.db_user, args.db_password),
    )


def resolve_admin_credentials(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> WpCredentials:
    """Build the administrative credentials, which are never defaulted.

    Falling back to the WordPress account would be privilege escalation by
    accident, and would also make the existence question unanswerable.
    """
    pair = args.admin_username or args.admin_password
    secret = args.admin_credentials_aws_secret_id

    if pair and secret:
        _fail(parser, "give either --admin-username/--admin-password or an AWS secret id")
    if not pair and not secret:
        _fail(
            parser,
            "administrative credentials are required: give --admin-username and "
            "--admin-password, or --admin-credentials-aws-secret-id",
        )
    if secret:
        return WpCredentials.from_aws_secrets_manager(
            secret_id=secret, region=args.admin_credentials_aws_region
        )
    if not (args.admin_username and args.admin_password):
        _fail(parser, "give both --admin-username and --admin-password")
    return WpCredentials.from_username_and_password(args.admin_username, args.admin_password)


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=str(args.log_level).upper(), format="%(message)s")
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(str(args.log_level).upper(), logging.INFO)
        )
    )

    try:
        connection = resolve_connection(args, parser)
        database = WpDatabase(connection)

        if args.inspect:
            state = database.inspect()
            print(state.value)
            return Exit.OK if state.is_ready else Exit.NOT_READY

        result = database.ensure(resolve_admin_credentials(args, parser), force=args.force)
    except MissingDependencyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return Exit.CONFIGURATION
    except ConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return Exit.CONFIGURATION
    except CredentialsUnobtainableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return Exit.CREDENTIALS
    except DatabaseUnreachableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return Exit.UNREACHABLE
    except ProvisioningError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return Exit.PROVISIONING
    except (InvalidArgumentsError, InvalidIdentifierError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return Exit.USAGE

    if result.changed:
        for action in result.actions:
            print(action)
    else:
        print(f"{ConnectionState.READY.value}; nothing to do")
    return Exit.OK

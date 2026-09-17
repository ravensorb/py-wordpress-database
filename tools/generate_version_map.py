"""Regenerate the WordPress db_version map from the source of truth.

There is no authoritative machine-readable mapping of WordPress's
``$wp_db_version`` to release numbers. ``api.wordpress.org``'s version-check
endpoint does not carry the field, and the WordPress.org versions page has a
"DB Version" column that is hand-maintained and sparsely populated -- 7.1 is
filled in while 7.0 and the 6.9 series are blank.

So it is derived instead of enumerated:

* ``api.wordpress.org/core/stable-check/1.0/`` gives the authoritative roster
  of every released version.
* ``wp-includes/version.php`` at that release's tag in the WordPress/WordPress
  mirror gives its ``$wp_db_version``.

Run it with::

    uv run python tools/generate_version_map.py

It rewrites ``src/l3io/wp/database/_version_map.py``. Committing generated data
keeps the runtime network-free; regenerating is a maintenance task, not a
deployment step.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

STABLE_CHECK = "https://api.wordpress.org/core/stable-check/1.0/"
VERSION_PHP = "https://raw.githubusercontent.com/WordPress/WordPress/{tag}/wp-includes/version.php"
TARGET = Path(__file__).resolve().parent.parent / "src/l3io/wp/database/_version_map.py"

_DB_VERSION = re.compile(r"\$wp_db_version\s*=\s*(\d+)\s*;")

#: Oldest WordPress release this package supports. A support decision, not a
#: limit of the derivation -- $wp_db_version is readable back to 2.0.
DEFAULT_MIN_RELEASE = "5.0"
_TIMEOUT = 30
_WORKERS = 16


def fetch(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as response:  # noqa: S310
            return str(response.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError):
        return None


def releases() -> list[str]:
    body = fetch(STABLE_CHECK)
    if body is None:
        print("could not reach the stable-check endpoint", file=sys.stderr)
        raise SystemExit(1)
    return sorted(json.loads(body))


def db_version_of(tag: str) -> tuple[str, int | None]:
    body = fetch(VERSION_PHP.format(tag=tag))
    if body is None:
        return tag, None
    found = _DB_VERSION.search(body)
    return tag, int(found.group(1)) if found else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-release",
        default=DEFAULT_MIN_RELEASE,
        help=f"oldest WordPress release to include (default: {DEFAULT_MIN_RELEASE})",
    )
    args = parser.parse_args()
    floor = _sort_key(args.min_release)

    everything = releases()
    tags = [t for t in everything if _sort_key(t) >= floor]
    print(
        f"{len(everything)} released versions from stable-check; "
        f"{len(tags)} at or above {args.min_release}",
        file=sys.stderr,
    )

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        results = list(pool.map(db_version_of, tags))

    resolved = {tag: db for tag, db in results if db is not None}
    missed = [tag for tag, db in results if db is None]
    print(f"{len(resolved)} parsed, {len(missed)} without a parseable value", file=sys.stderr)
    if not resolved:
        print("nothing derived; refusing to write an empty map", file=sys.stderr)
        return 1

    # Keep the lowest release for each db_version: several releases share one,
    # and the lookup wants the first release that introduced it.
    by_db: dict[int, str] = {}
    for tag, db in sorted(resolved.items(), key=lambda kv: _sort_key(kv[0])):
        by_db.setdefault(db, tag)

    lines = [
        '"""WordPress ``$wp_db_version`` to release number.',
        "",
        "GENERATED FILE -- do not edit by hand.",
        "Regenerate with: uv run python tools/generate_version_map.py",
        "",
        f"Derived from {len(resolved)} of {len(tags)} released versions at or above",
        f"WordPress {args.min_release}, listed by api.wordpress.org/core/stable-check/1.0/,",
        "reading $wp_db_version from wp-includes/version.php at each release tag.",
        "",
        f"MIN_RELEASE = {args.min_release!r}",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "#: db_version -> the earliest WordPress release that reported it.",
        "DB_VERSION_TO_RELEASE: dict[int, str] = {",
    ]
    lines += [f'    {db}: "{tag}",' for db, tag in sorted(by_db.items())]
    lines += [
        "}",
        "",
        "#: Oldest release included, as a support decision.",
        f'MIN_RELEASE = "{args.min_release}"',
        "",
    ]
    TARGET.write_text("\n".join(lines))
    print(f"wrote {TARGET} with {len(by_db)} entries", file=sys.stderr)
    if missed:
        print(
            f"unparsed: {', '.join(missed[:10])}{'...' if len(missed) > 10 else ''}",
            file=sys.stderr,
        )
    return 0


def _sort_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) if part.isdigit() else 0 for part in version.split("."))


if __name__ == "__main__":
    sys.exit(main())

"""WordPress ``$wp_db_version`` to release number.

GENERATED FILE -- do not edit by hand.
Regenerate with: uv run python tools/generate_version_map.py

Derived from 328 of 328 released versions at or above
WordPress 5.0, listed by api.wordpress.org/core/stable-check/1.0/,
reading $wp_db_version from wp-includes/version.php at each release tag.

MIN_RELEASE = '5.0'
"""

from __future__ import annotations

#: db_version -> the earliest WordPress release that reported it.
DB_VERSION_TO_RELEASE: dict[int, str] = {
    43764: "5.0",
    44719: "5.1",
    45805: "5.3",
    47018: "5.4",
    48748: "5.5",
    49752: "5.6",
    51917: "5.9",
    53496: "6.0.1",
    55853: "6.3",
    56657: "6.4",
    57155: "6.5",
    58975: "6.7",
    60421: "6.8.2",
    60717: "6.9",
    61833: "7.0",
}

#: Oldest release included, as a support decision.
MIN_RELEASE = "5.0"

"""Build a synthetic Safari favicon cache for tests — NEVER the real one.

Creates a cache directory containing ``favicons.db`` (matching Safari's schema)
and a ``favicons/`` folder with files named ``MD5(uuid).upper()``.

Runnable directly:  python -m tests.fixture /tmp/refaver-fixture
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from refaver.favicons import filename_for_uuid

SCHEMA = """
CREATE TABLE page_url (url TEXT NOT NULL UNIQUE, uuid TEXT NOT NULL);
CREATE TABLE icon_info (
  uuid TEXT PRIMARY KEY NOT NULL, url TEXT NOT NULL, timestamp INTEGER,
  width INTEGER DEFAULT 0, height INTEGER DEFAULT 0,
  has_generated_representations INTEGER DEFAULT 0);
CREATE TABLE rejected_resources (
  page_url TEXT NOT NULL, icon_url TEXT NOT NULL, timestamp INTEGER,
  UNIQUE(page_url, icon_url));
CREATE TABLE database_info (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL);
"""

# Deterministic UUIDs for predictable assertions.
U_LOCAL = "11111111-1111-4111-8111-111111111111"  # localhost:5173 (live)
U_EXAMPLE = "22222222-2222-4222-8222-222222222222"  # example.com (live)
U_ROW_ORPHAN = "33333333-3333-4333-8333-333333333333"  # icon_info, no page_url
FILE_ORPHAN_NAME = "DEADBEEFDEADBEEFDEADBEEFDEADBEEF"  # file with no icon_info row


def build_cache(dest: Path) -> Path:
    """Create a fixture cache under ``dest``. Returns the cache dir path."""
    dest.mkdir(parents=True, exist_ok=True)
    favicons = dest / "favicons"
    favicons.mkdir(exist_ok=True)
    db = dest / "favicons.db"
    if db.exists():
        db.unlink()

    conn = sqlite3.connect(db)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO page_url (url, uuid) VALUES (?, ?)",
            [
                ("http://localhost:5173", U_LOCAL),
                ("http://localhost:5173/login", U_LOCAL),
                ("https://example.com", U_EXAMPLE),
            ],
        )
        conn.executemany(
            "INSERT INTO icon_info (uuid, url, timestamp) VALUES (?, ?, ?)",
            [
                (U_LOCAL, "http://localhost:5173/favicon.ico", 800000000),
                (U_EXAMPLE, "https://example.com/favicon.ico", 800000001),
                (U_ROW_ORPHAN, "http://orphan.test/favicon.ico", 700000000),
            ],
        )
        conn.execute(
            "INSERT INTO rejected_resources (page_url, icon_url, timestamp) VALUES (?, ?, ?)",
            ("http://localhost:5173", "http://localhost:5173/favicon.svg", 800000000),
        )
        conn.commit()
    finally:
        conn.close()

    # Files for every icon_info row (incl. the row-orphan), plus one file-orphan.
    for uuid in (U_LOCAL, U_EXAMPLE, U_ROW_ORPHAN):
        (favicons / filename_for_uuid(uuid)).write_bytes(b"\x00\x00\x01\x00fake-ico")
    (favicons / FILE_ORPHAN_NAME).write_bytes(b"\x89PNG\r\n\x1a\nfake-png")

    return dest


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/refaver-fixture")
    print(build_cache(out))

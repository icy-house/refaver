---
name: make-fixture
description: Build a synthetic Safari favicons.db (+ fake favicons/ dir) for tests. Use when writing or running refaver tests, or when you need a safe stand-in for the real Safari favicon cache. Never touch the real ~/Library/Safari/Favicon Cache.
---

# make-fixture

Create a throwaway favicon cache that matches Safari's real schema, so tests and
manual checks never go near the user's actual Safari data.

## Schema (must match production)
```sql
CREATE TABLE page_url (url TEXT NOT NULL UNIQUE, uuid TEXT NOT NULL);
CREATE TABLE icon_info (
  uuid TEXT PRIMARY KEY NOT NULL, url TEXT NOT NULL, timestamp INTEGER,
  width INTEGER DEFAULT 0, height INTEGER DEFAULT 0,
  has_generated_representations INTEGER DEFAULT 0);
CREATE TABLE rejected_resources (
  page_url TEXT NOT NULL, icon_url TEXT NOT NULL, timestamp INTEGER,
  UNIQUE(page_url, icon_url));
CREATE TABLE database_info (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL);
```

## How
Use the shared builder in the test suite rather than hand-rolling SQL:
`cli/tests/conftest.py` exposes a `favicon_cache` pytest fixture that returns a
`Path` to a temp cache dir containing `favicons.db` and a `favicons/` folder with
files named `MD5(uuid).upper()` for each `icon_info` row.

For ad-hoc use outside pytest:
```bash
python3 -m cli.tests.fixture /tmp/refaver-fixture   # builds a cache dir there
```

## Invariants
- Files in `favicons/` are named `MD5(uuid).upper()` (no extension) — keep the
  fixture consistent with this so `--gc`/`--hard` tests are meaningful.
- Include at least: a normal site, a site with a `rejected_resources` entry, a
  row-orphan (icon_info row not in page_url), and a file-orphan (extra file).
- NEVER write to `~/Library/Safari/Favicon Cache/`.

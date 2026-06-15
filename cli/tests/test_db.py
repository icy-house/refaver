"""Tests for the soft/hard/gc operations against a synthetic cache."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from refaver import db
from refaver.favicons import filename_for_uuid
from tests.fixture import FILE_ORPHAN_NAME, U_EXAMPLE, U_LOCAL, U_ROW_ORPHAN


def _db(cache: Path) -> Path:
    return cache / "favicons.db"


def _favicons(cache: Path) -> Path:
    return cache / "favicons"


def _count(cache: Path, sql: str, *params: object) -> int:
    conn = sqlite3.connect(_db(cache))
    try:
        return int(conn.execute(sql, params).fetchone()[0])
    finally:
        conn.close()


def test_soft_reset_clears_blocklist_and_expires(favicon_cache: Path) -> None:
    res = db.soft_reset(_db(favicon_cache), "http://localhost:5173")

    assert res.rejected_cleared == 1
    assert res.icons_expired == 1  # one distinct uuid, even across two pages
    # blocklist gone for the target only
    assert _count(favicon_cache, "SELECT COUNT(*) FROM rejected_resources") == 0
    # the target's icon is expired, others untouched
    assert _count(favicon_cache, "SELECT timestamp FROM icon_info WHERE uuid = ?", U_LOCAL) == 0
    assert _count(favicon_cache, "SELECT timestamp FROM icon_info WHERE uuid = ?", U_EXAMPLE) != 0


def test_soft_reset_does_not_delete_rows_or_files(favicon_cache: Path) -> None:
    db.soft_reset(_db(favicon_cache), "http://localhost:5173")
    pages = _count(
        favicon_cache,
        "SELECT COUNT(*) FROM page_url WHERE url LIKE 'http://localhost:5173%'",
    )
    assert pages == 2
    assert (_favicons(favicon_cache) / filename_for_uuid(U_LOCAL)).exists()


def test_hard_reset_deletes_rows_and_file(favicon_cache: Path) -> None:
    res = db.hard_reset(_db(favicon_cache), _favicons(favicon_cache), "http://localhost:5173")

    assert res.page_url_deleted == 2
    assert res.rejected_cleared == 1
    assert res.icon_info_deleted == 1
    assert filename_for_uuid(U_LOCAL) in res.files_deleted
    assert not (_favicons(favicon_cache) / filename_for_uuid(U_LOCAL)).exists()
    # untouched site survives
    assert (_favicons(favicon_cache) / filename_for_uuid(U_EXAMPLE)).exists()


def test_gc_dry_run_reports_without_deleting(favicon_cache: Path) -> None:
    res = db.gc(_db(favicon_cache), _favicons(favicon_cache), dry_run=True)

    assert U_ROW_ORPHAN in res.row_orphans
    assert FILE_ORPHAN_NAME in res.file_orphans
    assert res.files_deleted == []
    assert (_favicons(favicon_cache) / FILE_ORPHAN_NAME).exists()


def test_gc_removes_both_orphan_kinds(favicon_cache: Path) -> None:
    res = db.gc(_db(favicon_cache), _favicons(favicon_cache))

    assert not (_favicons(favicon_cache) / FILE_ORPHAN_NAME).exists()
    assert not (_favicons(favicon_cache) / filename_for_uuid(U_ROW_ORPHAN)).exists()
    assert _count(favicon_cache, "SELECT COUNT(*) FROM icon_info WHERE uuid = ?", U_ROW_ORPHAN) == 0
    # live icons remain
    assert (_favicons(favicon_cache) / filename_for_uuid(U_LOCAL)).exists()
    assert len(res.files_deleted) == 2

"""Favicon database operations: soft reset, hard reset, garbage collection.

All write operations assume Safari is quit and the db has been backed up by the
caller (see ``cli.py``). Writes run inside ``BEGIN EXCLUSIVE``.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from .favicons import file_for_uuid


@dataclass
class SoftResult:
    rejected_cleared: int = 0
    icons_expired: int = 0


@dataclass
class HardResult:
    page_url_deleted: int = 0
    rejected_cleared: int = 0
    icon_info_deleted: int = 0
    files_deleted: list[str] = field(default_factory=list)


@dataclass
class GcResult:
    file_orphans: list[str] = field(default_factory=list)
    row_orphans: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    dry_run: bool = False


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def _like(target: str) -> str:
    return target + "%"


def preview(db: Path, target: str) -> list[sqlite3.Row]:
    """Rows that a reset for ``target`` would affect (page -> icon mapping)."""
    with closing(_connect(db)) as conn:
        return list(
            conn.execute(
                """
                SELECT p.url AS page, i.uuid AS uuid, i.url AS icon, i.timestamp AS timestamp
                FROM page_url p JOIN icon_info i ON p.uuid = i.uuid
                WHERE p.url LIKE ?
                ORDER BY i.timestamp DESC
                """,
                (_like(target),),
            )
        )


def soft_reset(db: Path, target: str) -> SoftResult:
    """Non-destructive: clear the blocklist for the target and expire its icons.

    Safari then re-fetches the current favicon on next load and self-cleans the
    superseded row + file.
    """
    with closing(_connect(db)) as conn:
        conn.execute("BEGIN EXCLUSIVE")
        cur = conn.execute("DELETE FROM rejected_resources WHERE page_url LIKE ?", (_like(target),))
        rejected = cur.rowcount
        cur = conn.execute(
            """
            UPDATE icon_info SET timestamp = 0
            WHERE uuid IN (SELECT uuid FROM page_url WHERE url LIKE ?)
            """,
            (_like(target),),
        )
        expired = cur.rowcount
        conn.commit()
    return SoftResult(rejected_cleared=rejected, icons_expired=max(expired, 0))


def hard_reset(db: Path, favicons: Path, target: str) -> HardResult:
    """Destructive: delete the target's rows across the three tables AND its files.

    Files are resolved from uuids captured BEFORE the rows are deleted.
    """
    result = HardResult()
    with closing(_connect(db)) as conn:
        # Capture the TARGET's icon uuids before we delete its mappings.
        target_uuids = {
            row["uuid"]
            for row in conn.execute(
                "SELECT DISTINCT uuid FROM page_url WHERE url LIKE ?", (_like(target),)
            )
        }
        conn.execute("BEGIN EXCLUSIVE")
        cur = conn.execute("DELETE FROM page_url WHERE url LIKE ?", (_like(target),))
        result.page_url_deleted = cur.rowcount
        cur = conn.execute("DELETE FROM rejected_resources WHERE page_url LIKE ?", (_like(target),))
        result.rejected_cleared = cur.rowcount

        # Of the target's icons, delete only those NO LONGER referenced by any page
        # (an icon shared with another site is left alone). Unrelated pre-existing
        # orphans are GC's job, not reset's.
        still_referenced = {
            row["uuid"] for row in conn.execute("SELECT DISTINCT uuid FROM page_url")
        }
        to_delete = sorted(target_uuids - still_referenced)
        conn.executemany("DELETE FROM icon_info WHERE uuid = ?", [(u,) for u in to_delete])
        result.icon_info_deleted = len(to_delete)
        conn.commit()

    for uuid in to_delete:
        path = file_for_uuid(favicons, uuid)
        if path.exists():
            path.unlink()
            result.files_deleted.append(path.name)
    return result


def _all_icon_uuids(conn: sqlite3.Connection) -> list[str]:
    return [row["uuid"] for row in conn.execute("SELECT uuid FROM icon_info")]


def _row_orphan_uuids(conn: sqlite3.Connection) -> list[str]:
    return [
        row["uuid"]
        for row in conn.execute(
            "SELECT uuid FROM icon_info WHERE uuid NOT IN (SELECT uuid FROM page_url)"
        )
    ]


def gc(db: Path, favicons: Path, *, dry_run: bool = False) -> GcResult:
    """Remove row-orphans (+ files) and file-orphans.

    - row-orphan: icon_info row not referenced by any page_url -> delete row + file
    - file-orphan: file in favicons/ with no icon_info row     -> delete file
    """
    result = GcResult(dry_run=dry_run)
    with closing(_connect(db)) as conn:
        row_orphans = _row_orphan_uuids(conn)
        result.row_orphans = list(row_orphans)

        expected = {file_for_uuid(favicons, u).name for u in _all_icon_uuids(conn)}
        actual = {p.name for p in favicons.iterdir() if p.is_file()} if favicons.exists() else set()
        file_orphans = sorted(actual - expected)
        result.file_orphans = file_orphans

        if dry_run:
            return result

        if row_orphans:
            conn.execute("BEGIN EXCLUSIVE")
            conn.executemany("DELETE FROM icon_info WHERE uuid = ?", [(u,) for u in row_orphans])
            conn.commit()

    # Delete files for row-orphans + the file-orphans.
    for uuid in row_orphans:
        path = file_for_uuid(favicons, uuid)
        if path.exists():
            path.unlink()
            result.files_deleted.append(path.name)
    for name in file_orphans:
        path = favicons / name
        if path.exists():
            path.unlink()
            result.files_deleted.append(name)
    return result

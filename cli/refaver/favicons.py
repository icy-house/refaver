"""Mapping between a favicon UUID and its file on disk.

VERIFIED (300/300 against a live cache): a favicon file in the ``favicons/``
directory is named ``MD5(icon_info.uuid).upper()`` — the uuid hashed exactly as
stored (uppercase, with dashes), MD5 hex, upper-cased, no extension.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def filename_for_uuid(uuid: str) -> str:
    """Return the on-disk favicon filename for an ``icon_info.uuid``."""
    return hashlib.md5(uuid.encode("utf-8")).hexdigest().upper()  # noqa: S324 (not security)


def file_for_uuid(favicons_dir: Path, uuid: str) -> Path:
    """Return the full path to the favicon file for ``uuid``."""
    return favicons_dir / filename_for_uuid(uuid)

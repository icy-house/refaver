"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixture import build_cache


@pytest.fixture()
def favicon_cache(tmp_path: Path) -> Path:
    """A synthetic Safari favicon cache dir (db + favicons/) in a temp location."""
    return build_cache(tmp_path / "Favicon Cache")

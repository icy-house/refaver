"""End-to-end CLI tests via the synthetic cache and --cache-dir override.

Safari-quit and FDA checks are patched where needed so tests never touch the
real cache or depend on the environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from refaver import cli, safari


@pytest.fixture(autouse=True)
def _no_real_safari(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend Safari is quit and FDA is granted; we operate on the fixture cache.
    monkeypatch.setattr(safari, "is_safari_running", lambda: False)
    monkeypatch.setattr(safari, "check_access", lambda db: None)


def test_doctor_reports_paths(favicon_cache: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["--cache-dir", str(favicon_cache), "doctor"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "cache dir" in out
    assert "not running" in out


def test_reset_soft_default(favicon_cache: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["--cache-dir", str(favicon_cache), "reset", "http://localhost:5173"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Soft reset" in out
    assert "Backup:" in out


def test_reset_no_match(favicon_cache: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["--cache-dir", str(favicon_cache), "reset", "http://nope.test"])
    assert rc == 0
    assert "Nothing to do" in capsys.readouterr().out


def test_reset_hard_requires_confirmation(favicon_cache: Path) -> None:
    rc = cli.main(
        ["--cache-dir", str(favicon_cache), "reset", "http://localhost:5173", "--hard", "--yes"]
    )
    assert rc == 0


def test_gc_dry_run(favicon_cache: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["--cache-dir", str(favicon_cache), "gc", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "row-orphans" in out
    assert "dry run" in out

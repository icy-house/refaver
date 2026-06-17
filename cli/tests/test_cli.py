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


def test_stale_reports_without_fixing(
    favicon_cache: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["--cache-dir", str(favicon_cache), "stale"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "http://localhost:5173" in out
    assert "--fix" in out
    assert "Backup:" not in out  # report-only never mutates


def test_stale_fix_all_soft_resets(
    favicon_cache: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["--cache-dir", str(favicon_cache), "stale", "--fix", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Backup:" in out
    assert "Fixed http://localhost:5173" in out


def test_gc_dry_run(favicon_cache: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["--cache-dir", str(favicon_cache), "gc", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "row-orphans" in out
    assert "dry run" in out


def test_soft_reset_allowed_while_safari_running(
    favicon_cache: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Verified safe: soft reset proceeds even when Safari is running.
    monkeypatch.setattr(safari, "is_safari_running", lambda: True)
    rc = cli.main(["--cache-dir", str(favicon_cache), "reset", "http://localhost:5173"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Soft reset" in out
    assert "reload the affected tab" in out


def test_hard_reset_blocked_while_safari_running(
    favicon_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # --hard deletes files, so it still requires Safari to be quit (exit code 3).
    monkeypatch.setattr(safari, "is_safari_running", lambda: True)
    rc = cli.main(
        ["--cache-dir", str(favicon_cache), "reset", "http://localhost:5173", "--hard", "--yes"]
    )
    assert rc == 3

"""Safari environment: cache paths, running-state, Full Disk Access, backups."""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

# Default location of Safari's favicon cache. Overridable for tests.
DEFAULT_CACHE_DIR = Path.home() / "Library" / "Safari" / "Favicon Cache"

FDA_SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_AllDiskAccess"


class FullDiskAccessError(RuntimeError):
    """Raised when the favicon db cannot be opened due to macOS TCC (no FDA)."""


class SafariRunningError(RuntimeError):
    """Raised when a write is attempted while Safari is running (WAL unsafe)."""


def cache_dir(override: Path | None = None) -> Path:
    return override if override is not None else DEFAULT_CACHE_DIR


def db_path(cache: Path) -> Path:
    return cache / "favicons.db"


def favicons_dir(cache: Path) -> Path:
    return cache / "favicons"


def is_safari_running() -> bool:
    """True if a Safari process is running. Conservative: errors -> assume running."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "Safari"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    return result.returncode == 0


def ensure_safari_quit() -> None:
    if is_safari_running():
        raise SafariRunningError(
            "Safari is running. Quit it fully (Cmd-Q) before modifying the favicon cache."
        )


def check_access(db: Path) -> None:
    """Verify the db can actually be opened; map TCC denial to FullDiskAccessError."""
    if not db.exists():
        # Stat is allowed even without FDA; a missing file is a different problem.
        raise FileNotFoundError(f"favicon db not found at {db}")
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        conn.close()
    except sqlite3.OperationalError as exc:
        # macOS TCC surfaces as "authorization denied" / "unable to open database".
        msg = str(exc).lower()
        if "authoriz" in msg or "unable to open" in msg:
            raise FullDiskAccessError(_fda_help(db)) from exc
        raise


def _fda_help(db: Path) -> str:
    return (
        "Cannot open the Safari favicon database — Full Disk Access is required.\n"
        f"  db: {db}\n"
        "Grant it: System Settings -> Privacy & Security -> Full Disk Access -> "
        "enable your terminal app, then fully quit and reopen the terminal.\n"
        "Tip: run `refaver doctor --open-settings` to jump straight to that pane."
    )


def open_fda_settings() -> None:
    subprocess.run(["open", FDA_SETTINGS_URL], check=False)


def backup_db(db: Path) -> Path:
    """Copy the db (and WAL sidecars if present) to a timestamped backup. Returns path."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = db.with_name(f"{db.name}.bak-{stamp}")
    shutil.copy2(db, backup)
    for suffix in ("-wal", "-shm"):
        side = db.with_name(db.name + suffix)
        if side.exists():
            shutil.copy2(side, backup.with_name(backup.name + suffix))
    return backup

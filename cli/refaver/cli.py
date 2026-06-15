"""refaver command-line interface.

Commands:
  reset <url>     Reset the favicon for a site (soft by default; --hard to delete).
  gc              Garbage-collect orphaned favicon rows and files.
  nuke            Delete the entire favicon cache (Safari rebuilds it).
  doctor          Check Full Disk Access, Safari state, and cache paths.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__, db, safari


def _eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def _resolve_cache(args: argparse.Namespace) -> Path:
    return safari.cache_dir(Path(args.cache_dir) if args.cache_dir else None)


def _guard_access(cache: Path) -> Path:
    """Preflight for any operation: just verify Full Disk Access. Returns db path."""
    database = safari.db_path(cache)
    safari.check_access(database)  # raises FullDiskAccessError / FileNotFoundError
    return database


def _guard_writable(cache: Path) -> Path:
    """Preflight for FILE-deleting operations: FDA + Safari must be quit.

    Verified safe to write the db while Safari runs (WAL + BEGIN EXCLUSIVE), so
    the soft reset does NOT use this. Deleting favicon files out from under a
    running Safari is untested, so --hard / gc / nuke still require a quit.
    """
    database = _guard_access(cache)
    safari.ensure_safari_quit()  # raises SafariRunningError
    return database


def _apply_hint() -> None:
    """Tell the user how the change becomes visible."""
    if safari.is_safari_running():
        print("Safari is running — reload the affected tab (or restart Safari) to see it.")
    else:
        print("Relaunch Safari and load the site — the current favicon should appear.")


def _confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in {"y", "yes"}
    except EOFError:
        return False


def cmd_doctor(args: argparse.Namespace) -> int:
    cache = _resolve_cache(args)
    database = safari.db_path(cache)
    print(f"cache dir : {cache}")
    print(f"db        : {database} ({'exists' if database.exists() else 'MISSING'})")
    print(f"favicons/ : {safari.favicons_dir(cache)}")
    running = (
        "running (quit only for --hard/gc/nuke)" if safari.is_safari_running() else "not running"
    )
    print(f"Safari    : {running}")
    try:
        safari.check_access(database)
        print("access    : OK (Full Disk Access granted)")
        return 0
    except safari.FullDiskAccessError as exc:
        print("access    : DENIED")
        _eprint("\n" + str(exc))
        if args.open_settings:
            safari.open_fda_settings()
        return 2
    except FileNotFoundError as exc:
        _eprint(str(exc))
        return 1


def cmd_reset(args: argparse.Namespace) -> int:
    cache = _resolve_cache(args)
    # Soft reset is safe while Safari runs; --hard deletes files, so it requires a quit.
    database = _guard_writable(cache) if args.hard else _guard_access(cache)

    affected = db.preview(database, args.url)
    if not affected:
        print(f"No cached favicons match {args.url!r}. Nothing to do.")
        return 0

    print(f"{len(affected)} cached page(s) match {args.url!r}.")
    backup = safari.backup_db(database)
    print(f"Backup: {backup}")

    if args.hard:
        if not _confirm("Hard reset: delete rows AND favicon files?", args.yes):
            print("Aborted.")
            return 1
        hres = db.hard_reset(database, safari.favicons_dir(cache), args.url)
        print(
            f"Deleted: page_url={hres.page_url_deleted}, "
            f"rejected_resources={hres.rejected_cleared}, "
            f"icon_info={hres.icon_info_deleted}, files={len(hres.files_deleted)}"
        )
    else:
        sres = db.soft_reset(database, args.url)
        print(
            f"Soft reset: cleared {sres.rejected_cleared} blocklist row(s), "
            f"expired {sres.icons_expired} icon(s)."
        )
    _apply_hint()
    return 0


def cmd_gc(args: argparse.Namespace) -> int:
    cache = _resolve_cache(args)
    database = safari.db_path(cache)
    safari.check_access(database)
    if not args.dry_run:
        safari.ensure_safari_quit()
        backup = safari.backup_db(database)
        print(f"Backup: {backup}")
    res = db.gc(database, safari.favicons_dir(cache), dry_run=args.dry_run)
    print(f"row-orphans : {len(res.row_orphans)}")
    print(f"file-orphans: {len(res.file_orphans)}")
    if args.dry_run:
        print("(dry run — nothing deleted)")
    else:
        print(f"deleted {len(res.files_deleted)} file(s) and {len(res.row_orphans)} row(s).")
    return 0


def cmd_nuke(args: argparse.Namespace) -> int:
    cache = _resolve_cache(args)
    safari.check_access(safari.db_path(cache))
    safari.ensure_safari_quit()
    if not _confirm(f"Delete the ENTIRE favicon cache at {cache}?", args.yes):
        print("Aborted.")
        return 1
    shutil.rmtree(cache)
    print("Favicon cache removed. Safari will rebuild it on next launch.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="refaver", description=__doc__)
    parser.add_argument("--version", action="version", version=f"refaver {__version__}")
    parser.add_argument(
        "--cache-dir",
        help="Override the favicon cache directory (for testing).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_reset = sub.add_parser("reset", help="Reset the favicon for a site.")
    p_reset.add_argument("url", help="Page URL prefix, e.g. http://localhost:5173")
    p_reset.add_argument(
        "--hard", action="store_true", help="Delete rows and files instead of soft expiry."
    )
    p_reset.add_argument("-y", "--yes", action="store_true", help="Skip confirmation.")
    p_reset.set_defaults(func=cmd_reset)

    p_gc = sub.add_parser("gc", help="Garbage-collect orphaned rows and files.")
    p_gc.add_argument("--dry-run", action="store_true", help="Report only; do not delete.")
    p_gc.set_defaults(func=cmd_gc)

    p_nuke = sub.add_parser("nuke", help="Delete the entire favicon cache.")
    p_nuke.add_argument("-y", "--yes", action="store_true", help="Skip confirmation.")
    p_nuke.set_defaults(func=cmd_nuke)

    p_doctor = sub.add_parser("doctor", help="Check FDA, Safari state, and paths.")
    p_doctor.add_argument(
        "--open-settings", action="store_true", help="Open the Full Disk Access pane."
    )
    p_doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except safari.FullDiskAccessError as exc:
        _eprint(str(exc))
        return 2
    except safari.SafariRunningError as exc:
        _eprint(f"error: {exc}")
        return 3
    except FileNotFoundError as exc:
        _eprint(f"error: {exc}")
        return 1
    except KeyboardInterrupt:
        _eprint("Interrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

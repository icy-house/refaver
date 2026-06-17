# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 1 Python CLI: `reset` (soft default + `--hard`), `gc` (`--dry-run`),
  `nuke`, and `doctor`.
- `stale` command: scans the cache for likely-stale favicons (sites on Safari's
  `rejected_resources` blocklist, plus local dev origins whose icon is older than
  `--days`, default 4) and reports them most-affected first. `--fix` repairs the
  chosen sites via the non-destructive soft reset (`--yes` to fix all unattended).
- `clean` command: removes the `favicons.db.bak-*` backups (and their
  WAL/SHM sidecars) left by past fixes once you're happy with the result.
  `--keep N` retains the newest N, `--dry-run` previews. Every command that
  creates a backup now points to it.
- Full Disk Access detection with guidance and a `--open-settings` shortcut.
- Automatic database backup before every mutating command.
- Synthetic-fixture test suite; ruff + mypy + pytest CI on macOS.
- Self-contained zipapp (`refaver-<version>.pyz`) distribution — zero deps, runs
  under any Python 3.9+; Homebrew installs it via `:nounzip` and runs it in
  isolation mode, immune to broken pip / messy user-site Python.

### Changed
- Soft `reset` no longer requires quitting Safari — verified safe to write the db
  while Safari runs (WAL + exclusive transaction), and the change applies on a tab
  reload. `--hard`, `gc`, and `nuke` still require Safari to be quit.

[Unreleased]: https://github.com/icy-house/refaver/commits/main

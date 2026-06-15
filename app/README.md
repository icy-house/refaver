# refaver.app — Phase 2 (planned)

A small, **notarized** macOS app for non-technical / support use: one button to
reset the current site's favicon, with Full Disk Access **scoped to the app
itself** (no terminal-wide grant).

## Why a separate app

- Tool-targeted FDA needs a compiled binary with a stable code identity; a
  shell-run script's FDA attaches to the terminal/`python3`, not the tool.
- A notarized `.app` avoids Gatekeeper friction for users who won't use a CLI.

## Planned design

- Swift + SwiftPM. Reimplements the ~30 lines of reset/gc logic (no shared code
  with the Python CLI — the logic is tiny and specified in
  [`../FAVICON_RESET_RESEARCH.md`](../FAVICON_RESET_RESEARCH.md)).
- Same invariants as the CLI: soft-first, backup, `BEGIN EXCLUSIVE`, Safari-quit
  guard.
- Distribution: signed + notarized with a Developer ID; `.dmg` and/or
  `brew install --cask`.

## Status

Not started. The Python CLI (`../cli/`) is the reference implementation. Release
plumbing is stubbed in `.github/workflows/release.yml` (`release-app`, commented)
and `packaging/`.

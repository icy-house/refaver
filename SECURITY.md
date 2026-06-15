# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories
("Report a vulnerability" on the repo's Security tab) rather than a public issue.
We aim to acknowledge within 7 days.

## Why refaver needs Full Disk Access

Safari stores favicons in `~/Library/Safari/Favicon Cache/`, which macOS protects
with TCC. There is **no Safari or WebExtension API** to reset a favicon, so the
only way to do it is to edit `favicons.db` directly — which requires Full Disk
Access. This is an inherent constraint, not a design choice.

## What that means for you

Granting **Full Disk Access to your terminal** gives *every* program you run in
that terminal access to all protected files for as long as the grant stands. That
is a real, broad privilege. We make it as safe as we can:

- **Default mode is non-destructive.** `refaver reset` only clears a blocklist row
  and expires a timestamp; Safari does the rest. No files are deleted by default.
- **Backups.** Every mutating command copies `favicons.db` to a timestamped backup
  first.
- **Guards.** Writes refuse to run while Safari is running, and run inside an
  exclusive transaction.
- **Scoped queries.** Operations target the URL prefix you pass; `--hard` only
  deletes icons belonging to that site.

## Lower-privilege option (Phase 2)

For non-technical / support scenarios, the planned notarized `.app` receives Full
Disk Access **scoped to the app itself** — not your whole terminal — which avoids
leaving a terminal-wide hole open. Prefer it when you don't need the CLI.

## Supported versions

The latest released version receives fixes. refaver is macOS-only.

# refaver

**Reset Safari's cached favicons for a site — without Terminal gymnastics.**

Safari caches favicons in a private store that survives "Clear History," cache
emptying, and hard reloads. During local development (e.g. `localhost:5173`) a
changed favicon can stay stuck for days. `refaver` fixes it in one command.

> macOS only · Safari 14+ · MIT licensed

## Quick start

```bash
brew install icy-house/tap/refaver    # or: pipx install refaver

refaver doctor                        # check Full Disk Access + paths
# Quit Safari, then:
refaver reset http://localhost:5173   # soft, non-destructive
# Relaunch Safari — the current favicon appears.
```

## Requirements

- **Full Disk Access.** Safari's favicon store is TCC-protected; without FDA the
  database cannot be opened at all. Grant it once:
  **System Settings → Privacy & Security → Full Disk Access → enable your terminal**,
  then fully quit and reopen the terminal. (`refaver doctor --open-settings` jumps
  there.)
- **Safari fully quit** before any reset (the database uses SQLite WAL mode).

## Commands

| Command | What it does |
|---|---|
| `refaver reset <url>` | **Soft** reset (default): clears the site's blocklist entry and expires its icon so Safari re-fetches and self-cleans. Non-destructive. |
| `refaver reset <url> --hard` | Deletes the site's rows **and** icon files. Use only if soft doesn't take. |
| `refaver gc [--dry-run]` | Removes orphaned favicon rows/files left by other tools. |
| `refaver nuke` | Deletes the entire favicon cache; Safari rebuilds it. |
| `refaver doctor` | Reports FDA status, Safari state, and cache paths. |

Every mutating command **backs up the database first** (`favicons.db.bak-*`).

## How it works

Safari maps each page to a favicon UUID in `favicons.db`. A favicon gets "stuck"
because its URL lands in a **blocklist** table (`rejected_resources`) that Safari
never retries — even after the server starts serving the icon correctly. The soft
reset clears that blocklist entry and marks the icon expired; on next launch Safari
re-fetches the current favicon and removes the stale row + file itself.

The full reverse-engineering write-up — including why there's no Safari API for
this and how the on-disk files are named — is in
[`FAVICON_RESET_RESEARCH.md`](FAVICON_RESET_RESEARCH.md).

## Security

`refaver` needs Full Disk Access, which is powerful. See [`SECURITY.md`](SECURITY.md)
for what that means, why the default mode is non-destructive, and the safer
app-based distribution (Phase 2) for non-technical users.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: `ruff`, `mypy`, `pytest` must
pass; DB-touching changes follow the `db-safety-check` checklist and test against a
synthetic fixture — never your real Safari cache.

## Roadmap

- **Phase 1 (this):** Python CLI, Homebrew, for developers.
- **Phase 2:** a small notarized `.app` with a one-click button and tool-scoped
  Full Disk Access — for non-technical / support use, no Terminal-wide grant.

# refaver — Claude project rules

`refaver` resets Safari's cached favicons for a site without Terminal gymnastics.
macOS only, Safari 14+. See `FAVICON_RESET_RESEARCH.md` for the full, experimentally
verified background — it is the spec; trust it over assumptions.

## Architecture (verified)
- **Soft-first.** The default reset is NON-destructive: clear the target's rows in
  `rejected_resources` and set `icon_info.timestamp = 0`; Safari re-fetches and
  self-cleans on next launch. Covers both the "icon changed, same URL" case and the
  rename + blocklist case.
- `--hard` = delete `page_url` + `rejected_resources` + orphaned `icon_info`, AND
  delete the icon files. Only when soft fails to take.
- `--gc` = remove file-orphans (file with no `icon_info` row) and row-orphans
  (`icon_info` row not referenced by any `page_url`) + their files.
- Favicon filename = `MD5(icon_info.uuid).upper()`. Needed only for `--hard`/`--gc`.

## Hard facts (do not re-litigate)
- There is NO Safari/WebExtensions API to reset a favicon. Direct DB edits only.
- Full Disk Access is MANDATORY: without it, sqlite cannot even open the db
  ("authorization denied"). The CLI must catch that and guide the user.
- The blocklist table `rejected_resources` is the usual reason a favicon is "stuck".
- Safari must be fully QUIT before writing the db (WAL mode).

## Safety invariants (enforced by hook + reviews)
1. NEVER read/write the user's real `~/Library/Safari/Favicon Cache/` from tests or
   automated runs. Tests use a synthetic fixture db (`make-fixture` skill).
2. Every db mutation: back up the db first, use `BEGIN EXCLUSIVE`, and refuse to run
   while Safari is running.
3. Destructive commands (`--hard`, `nuke`) require explicit confirmation (`--yes` to
   bypass in scripts).
4. Prefer soft mode. Reach for deletion only when the soft path is proven insufficient.

## Code standards
- **CLI (Phase 1): Python 3.9+, standard library ONLY** (`sqlite3`, `hashlib`,
  `argparse`, `pathlib`, `subprocess`). No third-party runtime deps.
- Format + lint with **ruff**; type-check with **mypy** (`--strict` where practical).
- Full type hints. Small, pure functions for db/path logic; side effects isolated.
- Tests with **pytest** against fixtures; aim to cover soft/hard/gc paths.
- App (Phase 2): Swift, reimplements the ~30 lines of logic — no shared code with Python.

## Conventions
- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `ci:`).
- Keep `CHANGELOG.md` (Keep a Changelog format) updated for user-facing changes.
- One logical change per PR; CI (ruff + mypy + pytest on macOS) must pass.
- End commit messages with the Co-Authored-By trailer when written by Claude.

---
name: db-safety-check
description: Safety checklist to apply before merging any change that mutates favicons.db. Use when reviewing or writing code that deletes/updates favicon DB rows or files, or touches the reset/gc/nuke paths.
---

# db-safety-check

Run through this before any change that writes to the favicon cache lands.

## Checklist
- [ ] **Soft-first**: is deletion actually required, or does the soft path suffice?
- [ ] **Backup**: the db is copied (timestamped `.bak-*`) before the first write.
- [ ] **Exclusive write**: mutations run inside `BEGIN EXCLUSIVE`.
- [ ] **Safari guard**: the command refuses to run while Safari is running.
- [ ] **FDA handling**: an "authorization denied" / open failure is caught and the
      user is told to grant Full Disk Access (and the settings pane is offered).
- [ ] **File order**: for `--hard`/`--gc`, icon files (`MD5(uuid).upper()`) are
      computed/deleted using uuids captured BEFORE the rows are deleted.
- [ ] **Confirmation**: destructive ops require `--yes` or an interactive prompt.
- [ ] **Tests**: new behavior is covered by a pytest test using the fixture cache
      (`make-fixture`), never the real `~/Library/Safari/Favicon Cache/`.
- [ ] **Dry run**: `--gc`/`--hard` support (or are tested with) a `--dry-run` that
      reports what would change without writing.

## Red flags — stop and reconsider
- Any code path that can touch `~/Library/Safari/Favicon Cache/` in a test.
- Writing the db without a prior backup or without the Safari-quit guard.
- Deleting files by a name derived from anything other than `MD5(uuid).upper()`.

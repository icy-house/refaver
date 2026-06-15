# Contributing to refaver

Thanks for helping! refaver is small and safety-critical (it edits Safari's
database), so the bar is: **clear, tested, and incapable of corrupting a user's
real cache.**

## Dev setup

```bash
cd cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Before you open a PR

```bash
ruff check . && ruff format --check .
mypy refaver
pytest -q
```

All three must pass; CI runs them on `macos-latest`.

## Safety rules (non-negotiable)

- **Never** read or write the real `~/Library/Safari/Favicon Cache/` from tests or
  automated code. Tests use a synthetic fixture (`tests/fixture.py`).
- Any code that mutates the database must: back up first, run inside
  `BEGIN EXCLUSIVE`, and refuse to run while Safari is running.
- Prefer the **soft** (non-destructive) path. Deletion is a fallback.
- For DB-touching changes, walk the `db-safety-check` checklist
  (`.claude/skills/db-safety-check/`).

The repo ships a Claude Code hook that blocks destructive shell commands aimed at
the real cache during development — but don't rely on it; write safe code.

## Style & commits

- Standard library only for the CLI (no runtime dependencies).
- Full type hints; small pure functions for db/path logic.
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`.
- Update `CHANGELOG.md` for user-facing changes.

## Releasing (maintainers)

See `.claude/skills/cut-release/`. Tag `vX.Y.Z` → the release workflow builds and
publishes.

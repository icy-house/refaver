---
name: cut-release
description: Cut a refaver release — bump version, update CHANGELOG, tag, and push so the GitHub release pipeline runs. Use when the user asks to release, publish, or ship a new version.
---

# cut-release

Drive a versioned release of the Phase-1 CLI (and, later, the Phase-2 app).

## Steps
1. Decide the version (SemVer). Confirm with the user if ambiguous.
2. Update `cli/pyproject.toml` `version`.
3. Move `CHANGELOG.md` `[Unreleased]` items under a new `## [X.Y.Z] - YYYY-MM-DD`.
4. Commit: `chore(release): vX.Y.Z`.
5. Tag: `git tag vX.Y.Z` and push branch + tag.
   - Pushing the tag triggers `.github/workflows/release.yml`, which builds,
     ad-hoc signs the CLI, creates the GitHub Release, and bumps the Homebrew tap.
6. Phase 2 only: the same workflow signs + NOTARIZES the `.app` using the
   `MACOS_*` GitHub Secrets (Developer ID). Verify those secrets exist first.

## Guardrails
- CI (ruff + mypy + pytest) must be green on the release commit.
- Never publish with failing tests or an empty CHANGELOG entry.
- Only commit/tag/push when the user explicitly asks to release.
- Confirm the tag does not already exist.

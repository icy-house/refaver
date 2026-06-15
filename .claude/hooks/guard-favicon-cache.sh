#!/usr/bin/env bash
#
# refaver dev safety hook (PreToolUse / Bash).
#
# Blocks DESTRUCTIVE shell commands that target the user's REAL Safari favicon
# cache, so automated coding can never corrupt your own Safari while developing.
# Read-only inspection (ls, sqlite3 SELECT, cp-to-backup) is allowed.
#
# Contract: reads the tool-call JSON on stdin; exit 2 + stderr = block.

set -euo pipefail
input="$(cat)"

# Extract the command string (python3 is always present on dev macs / CI).
cmd="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
[ -z "$cmd" ] && exit 0

# Only care about the real cache path (allow temp/fixture dbs elsewhere).
case "$cmd" in
  *"Library/Safari/Favicon Cache"*) : ;;
  *) exit 0 ;;
esac

# Destructive verbs against that path -> block.
if printf '%s' "$cmd" | grep -Eiq '(\brm\b|\bmv\b|\btrash\b|sqlite3[^|]*(DELETE|UPDATE|INSERT|DROP|REPLACE)|>[^>]|>>|truncate)'; then
  echo "refaver guard: blocked a destructive command against the REAL Safari favicon cache." >&2
  echo "Tests/automation must use a synthetic fixture db, never ~/Library/Safari/Favicon Cache/." >&2
  echo "If this is a deliberate manual action, run it yourself in your own terminal." >&2
  exit 2
fi

exit 0

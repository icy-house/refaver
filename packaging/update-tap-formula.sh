#!/usr/bin/env bash
#
# Rewrite a Homebrew formula's version, .pyz URL, and sha256 in place.
# Used by the release workflow to bump the tap automatically — no manual sha.
#
# Usage:  ./packaging/update-tap-formula.sh <version> <sha256> <formula_path>
#   e.g.  ./packaging/update-tap-formula.sh 0.1.1 abc123... tap/Formula/refaver.rb

set -euo pipefail
VERSION="$1"   # without leading "v"
SHA="$2"
FORMULA="$3"

python3 - "$VERSION" "$SHA" "$FORMULA" <<'PY'
import re, sys

version, sha, path = sys.argv[1], sys.argv[2], sys.argv[3]
src = open(path).read()

src, n_url = re.subn(
    r'releases/download/v[0-9][^/"]*/refaver-[0-9][^"]*\.pyz',
    f'releases/download/v{version}/refaver-{version}.pyz',
    src,
)
src, n_ver = re.subn(r'version "[^"]*"', f'version "{version}"', src)
src, n_sha = re.subn(r'sha256 "[^"]*"', f'sha256 "{sha}"', src)

if not (n_url and n_ver and n_sha):
    sys.exit(f"formula not updated cleanly (url={n_url}, version={n_ver}, sha={n_sha})")

open(path, "w").write(src)
print(f"updated {path} -> v{version}, sha {sha[:12]}…")
PY

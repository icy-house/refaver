#!/usr/bin/env bash
#
# Build a self-contained zipapp (refaver-<version>.pyz) from the CLI package.
#
# A zipapp is a single executable zip of pure-Python sources. refaver has zero
# third-party dependencies, so the .pyz runs under ANY Python 3.9+ with no pip,
# no virtualenv, and no exposure to a messy user/site Python setup.
#
# Usage:  ./packaging/build-pyz.sh [output_dir]   (default: <repo>/dist)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/dist}"
mkdir -p "$OUT"

# Version comes from the package itself (single source of truth).
VERSION="$(cd "$ROOT/cli" && python3 -c 'import refaver; print(refaver.__version__)')"

BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

cp -R "$ROOT/cli/refaver" "$BUILD/refaver"
find "$BUILD" -name '__pycache__' -type d -prune -exec rm -rf {} +

PYZ="$OUT/refaver-$VERSION.pyz"
python3 -m zipapp "$BUILD" \
  --main "refaver.cli:main" \
  --python "/usr/bin/env python3" \
  --output "$PYZ"

echo "$PYZ"

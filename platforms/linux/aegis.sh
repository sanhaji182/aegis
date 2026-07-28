#!/bin/bash
# aegis.sh — Linux / WSL launcher.
#
# Usage:
#   ./aegis.sh                       (reads ~/.aegis/prompt.txt)
#   ./aegis.sh "your prompt here"    (inline payload)
#
# Works on any Linux distro with python3 in PATH.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"

PY="${PYTHON:-python3}"

# Prefer aegis on PATH; fall back to repo-local aegis.py.
if command -v aegis >/dev/null 2>&1; then
    if [ $# -gt 0 ]; then
        exec aegis "$@"
    else
        exec aegis
    fi
fi

PY_SCRIPT="$ROOT/aegis.py"
if [ ! -f "$PY_SCRIPT" ]; then
    echo "[!] aegis.py not found at $PY_SCRIPT"
    echo "    Run bash install.sh first."
    exit 2
fi

cd "$ROOT"
if [ $# -gt 0 ]; then
    exec "$PY" "$PY_SCRIPT" "$@"
else
    exec "$PY" "$PY_SCRIPT"
fi

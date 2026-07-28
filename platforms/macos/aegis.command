#!/bin/bash
# aegis.command — macOS Finder double-clickable launcher.
#
# Double-click this file from Finder. A Terminal window opens, runs
# `aegis` with the prompt from ~/.aegis/prompt.txt, and shows the response.
# Inline payloads are passed as $1.

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
    echo "    Run 'bash install.sh' first, or set PYTHON=aegis-bin-path."
    exit 2
fi

echo "[+] using local $PY_SCRIPT"
cd "$ROOT"
if [ $# -gt 0 ]; then
    exec "$PY" "$PY_SCRIPT" "$@"
else
    exec "$PY" "$PY_SCRIPT"
fi

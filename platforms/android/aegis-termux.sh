#!/data/data/com.termux/files/usr/bin/bash
# aegis-termux.sh — Android Termux launcher.
#
# Setup (once):
#   1. Install Termux: https://f-droid.org/packages/com.termux/
#   2. Inside Termux:
#        pkg install python git
#        git clone https://github.com/xscope0/hermes.git
#        cd hermes
#        bash install.sh
#
# Usage:
#   ./aegis-termux.sh                       (reads ~/.aegis/prompt.txt)
#   ./aegis-termux.sh "your prompt here"    (inline payload)
#
# Termux notes:
#   - /sdcard/ is mounted via Storage Access Framework, not direct paths.
#   - HERMES_HOME / AEGIS_HOME defaults to $HOME (~) which is fine on Termux.
#   - API keys: store in ~/.aegis/env (mode 600) and `source ~/.aegis/env`.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"

PY="${PYTHON:-python3}"

# Termux prefers aegis on PATH after `pip install -e .`.
if command -v aegis >/dev/null 2>&1; then
    if [ $# -gt 0 ]; then
        exec aegis "$@"
    else
        exec aegis
    fi
fi

PY_SCRIPT="$ROOT/aegis.py"
if [ ! -f "$PY_SCRIPT" ]; then
    echo "[!] aegis.py not found at $PY_SCRIPT" >&2
    echo "    Run bash install.sh first." >&2
    exit 2
fi

cd "$ROOT"
if [ $# -gt 0 ]; then
    exec "$PY" "$PY_SCRIPT" "$@"
else
    exec "$PY" "$PY_SCRIPT"
fi

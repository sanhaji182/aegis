#!/bin/bash
# AEGIS v1.0 Installer — Split Architecture
# Clean persona + encrypted payload + runtime loader
#
# Flow:
#   methods/ (plaintext in repo) → assemble → payload.json → encrypt → vault.dat
#   vault.dat encrypted with YOUR key, not author's key.
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${GREEN}🪽 AEGIS v1.0 Installer${NC}"
echo -e "${GREEN}   海鸥 Persona × Attack Triad Framework${NC}"
echo -e "${GREEN}   Split Architecture — Clean Persona + Encrypted Payload${NC}"
echo ""

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
AEGIS_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$HERMES_HOME/skills/aegis"

# Pick a Python that exists
PY=""
for cand in python3 python /opt/homebrew/bin/python3 /usr/bin/python3 \
            "$HOME/.local/bin/python3" /usr/local/bin/python3; do
    if command -v "$cand" >/dev/null 2>&1; then
        PY="$(command -v "$cand")"
        break
    fi
done

# ─── 1. Install Python dependencies ───────────────────
echo -e "${YELLOW}[1/5]${NC} Installing Python dependencies..."
if [ -z "$PY" ]; then
    echo -e "${RED}  ✗ no python3 found${NC}"
    exit 1
fi
if "$PY" -c "import cryptography" 2>/dev/null; then
    echo "  ✓ cryptography (already installed)"
else
    "$PY" -m pip install -q cryptography 2>/dev/null && echo "  ✓ cryptography" || {
        echo -e "${RED}  ✗ cryptography install failed${NC}"
        echo "    $PY -m pip install cryptography"
        exit 1
    }
fi

# ─── 2. Register as Hermes skill (clean persona) ──────
echo -e "${YELLOW}[2/5]${NC} Registering Hermes skill..."
mkdir -p "$SKILL_DIR"
cp "$AEGIS_DIR/SKILL.md" "$SKILL_DIR/SKILL.md" && echo "  ✓ SKILL.md"
cp "$AEGIS_DIR/AEGIS_SOUL.md" "$SKILL_DIR/system-prompt.txt" && echo "  ✓ system-prompt.txt"
cp "$AEGIS_DIR/config/prefill.json" "$SKILL_DIR/prefill.json" 2>/dev/null && echo "  ✓ prefill.json" || echo "  ⚠ prefill.json skipped"

# ─── 3. Generate YOUR key ─────────────────────────────
echo -e "${YELLOW}[3/5]${NC} Generating AES-256 encryption key..."
python3 "$AEGIS_DIR/loader/loader.py" init 2>/dev/null && echo "  ✓ Key generated (your key, not author's)" || {
    echo -e "${RED}  ✗ Key generation failed${NC}"
    exit 1
}

# ─── 4. Build vault from source ───────────────────────
echo -e "${YELLOW}[4/5]${NC} Building encrypted vault from methods/ ..."
python3 "$AEGIS_DIR/loader/loader.py" build 2>/dev/null && echo "  ✓ Vault built with your key" || {
    echo -e "${RED}  ✗ Vault build failed${NC}"
    echo "    Manual: cd $AEGIS_DIR && python3 loader/loader.py build"
    exit 1
}

# ─── 5. Verify vault ──────────────────────────────────
echo -e "${YELLOW}[5/5]${NC} Verifying vault integrity..."
python3 "$AEGIS_DIR/loader/loader.py" verify 2>/dev/null && echo "  ✓ Vault OK — encrypted with your key" || {
    echo -e "${RED}  ✗ Verification failed${NC}"
    exit 1
}

# ─── Permissions ──────────────────────────────────────
chmod +x "$AEGIS_DIR/loader/loader.py" 2>/dev/null || true
chmod 600 "$AEGIS_DIR/payload/.key" 2>/dev/null || true

# ─── Done ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}✅ AEGIS v1.0 installed!${NC}"
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ⚠️  SPLIT ARCHITECTURE — DUA LOKASI BERBEDA           ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                        ║"
echo "║  PERSONA (hanya 3 file):                               ║"
echo "║  $SKILL_DIR/"
echo "║  └─ SKILL.md, system-prompt.txt, prefill.json"
echo "║                                                        ║"
echo "║  TOOLS (full framework):                               ║"
echo "║  $AEGIS_DIR"
echo "║  └─ loader/, payload/, methods/ (36 files)             ║"
echo "║                                                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo -e "${YELLOW}Jika cek ~/.hermes/skills/aegis/ — memang cuma 3 file.${NC}"
echo -e "${YELLOW}Itu PERSONA LAYER. Tools-nya di:${NC}"
echo -e "${GREEN}$AEGIS_DIR${NC}"
echo ""
echo "Commands:"
echo "  hermes --skills aegis -z 'your prompt'            # Trigger AEGIS"
echo "  python3 $AEGIS_DIR/loader/loader.py decrypt       # Inject vault"
echo "  python3 $AEGIS_DIR/loader/loader.py locks         # List persona locks"
echo "  python3 $AEGIS_DIR/loader/loader.py lock triple 'query'  # Unskippable lock"
echo ""
echo -e "${GREEN}🪽 海鸥在线,你要整点薯条吗?${NC}"
#!/bin/bash
# ─────────────────────────────────────────────────────────
#  Hetzner Cloud MCP Server - Installasjonsskript
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "🔧 Hetzner Cloud MCP Server - Installasjon"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Sjekk Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 er ikke installert. Installer Python 3.10+ først."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION funnet"

# Opprett virtuelt miljø
echo "📦 Oppretter virtuelt miljø..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Installer avhengigheter
echo "📥 Installerer avhengigheter..."
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q

echo ""
echo "✅ Installasjon fullført!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Neste steg:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Sett API-nøkkelen din som miljøvariabel:"
echo ""
echo "   export HETZNER_API_TOKEN='din-hetzner-api-token'"
echo ""
echo "2. Legg til i Claude Desktop config:"
echo "   (Mac: ~/Library/Application Support/Claude/claude_desktop_config.json)"
echo "   (Win: %APPDATA%\\Claude\\claude_desktop_config.json)"
echo ""
cat << 'JSONEOF'
{
  "mcpServers": {
    "hetzner": {
      "command": "VENV_PATH/bin/python",
      "args": ["SERVER_PATH/server.py"],
      "env": {
        "HETZNER_API_TOKEN": "din-token-her",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
JSONEOF
echo ""
echo "   Bytt ut stiene:"
echo "   VENV_PATH  → $VENV_DIR"
echo "   SERVER_PATH → $SCRIPT_DIR"
echo ""
echo "3. Start Claude Desktop på nytt"
echo ""

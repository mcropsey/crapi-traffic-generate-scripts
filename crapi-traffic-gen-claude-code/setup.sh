#!/usr/bin/env bash
# setup.sh — one-time environment bootstrap for crapi-traffic-gen
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# What it does:
#   1. Checks for Python 3.9+
#   2. Creates a .venv virtual environment in this directory
#   3. Installs dependencies from requirements.txt
#   4. Verifies connectivity to crAPI and Mailhog
#   5. Prints the command to activate the venv and run the script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
CONFIG="$SCRIPT_DIR/config.ini"

# ── colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
fail() { echo -e "${RED}  ✗${NC} $*"; exit 1; }

echo
echo "════════════════════════════════════════════════════"
echo "  crAPI Noname Traffic Generator — Setup"
echo "════════════════════════════════════════════════════"
echo

# ── 1. Python version ─────────────────────────────────────────────────────────
PYTHON=$(command -v python3 || command -v python || true)
[[ -z "$PYTHON" ]] && fail "Python not found. Install Python 3.9+ and try again."

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")

if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 9 ) ]]; then
    fail "Python 3.9+ required (found $PY_VERSION). Please upgrade."
fi
ok "Python $PY_VERSION found at $PYTHON"

# ── 2. Create virtual environment ─────────────────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
    warn ".venv already exists — skipping creation (delete it to recreate)"
else
    echo "  Creating virtual environment at .venv …"
    "$PYTHON" -m venv "$VENV_DIR"
    ok "Virtual environment created"
fi

# Point at the venv binaries for the rest of this script
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# ── 3. Install / upgrade dependencies ─────────────────────────────────────────
echo "  Installing dependencies from requirements.txt …"
"$VENV_PIP" install --quiet --upgrade pip
"$VENV_PIP" install --quiet -r "$SCRIPT_DIR/requirements.txt"
ok "Dependencies installed"

# Show what's installed
echo
echo "  Installed packages:"
"$VENV_PIP" list --format=columns | grep -E "(requests|urllib3|Package)"
echo

# ── 4. Parse URLs from config.ini ─────────────────────────────────────────────
read_ini() {
    # read_ini <file> <section> <key>
    python3 -c "
import configparser, sys
c = configparser.ConfigParser()
c.read('$1')
print(c.get('$2', '$3', fallback=''))
"
}

CRAPI_URL=$(read_ini "$CONFIG" "targets" "crapi_base_url")
MAILHOG_URL=$(read_ini "$CONFIG" "targets" "mailhog_base_url")

# ── 5. Connectivity checks ────────────────────────────────────────────────────
echo "  Checking connectivity …"

check_url() {
    local label="$1" url="$2"
    if curl -sk --max-time 8 --output /dev/null --write-out "%{http_code}" "$url" | grep -qE "^[123]"; then
        ok "$label reachable ($url)"
    else
        warn "$label not reachable ($url) — check your config.ini and VPN/network"
    fi
}

check_url "crAPI"    "$CRAPI_URL/apidocs"
check_url "Mailhog"  "$MAILHOG_URL/api/v2/messages"

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo
echo "════════════════════════════════════════════════════"
echo "  Setup complete."
echo "════════════════════════════════════════════════════"
echo
echo "  To run the traffic generator:"
echo
echo "    source .venv/bin/activate"
echo "    python crapi_traffic_gen.py"
echo
echo "  Or use the wrapper (no manual activation needed):"
echo
echo "    ./run.sh"
echo "    ./run.sh --users 10 --iterations 5 --delay 0.3"
echo

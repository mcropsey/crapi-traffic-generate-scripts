#!/usr/bin/env bash
# run.sh — activate the venv and run the traffic generator
#
# Usage:
#   ./run.sh                              # use config.ini defaults
#   ./run.sh --users 10 --iterations 5   # pass args through to the script
#   ./run.sh --help                       # show all options
#
# If .venv does not exist, run ./setup.sh first.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "ERROR: .venv not found. Run ./setup.sh first." >&2
    exit 1
fi

exec "$VENV_PYTHON" "$SCRIPT_DIR/crapi_traffic_gen.py" "$@"

#!/usr/bin/env bash
# Startet den Eventwochen-Reporter unter Linux/macOS.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 fehlt. Unter Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Lege virtuelle Umgebung an (.venv) ..."
  "$PYTHON_BIN" -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
elif [[ ! -x .venv/bin/python ]]; then
  echo ".venv ist kaputt – neu anlegen mit: rm -rf .venv && ./run.sh"
  exit 1
fi

mkdir -p output snapshots data
if [[ -f eventwochen.db && ! -f data/eventwochen.db ]]; then
  cp -n eventwochen.db data/eventwochen.db 2>/dev/null || cp eventwochen.db data/eventwochen.db
fi

export DB_PATH="${DB_PATH:-$PWD/data/eventwochen.db}"
export OUTPUT_DIR="${OUTPUT_DIR:-$PWD/output}"
export SNAPSHOT_DIR="${SNAPSHOT_DIR:-$PWD/snapshots}"

echo "Starte auf http://127.0.0.1:${PORT:-5151} ..."
exec .venv/bin/python app.py

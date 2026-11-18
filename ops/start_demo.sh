#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x "venv/bin/python" ]]; then
  PYTHON_BIN="venv/bin/python"
elif [[ -x "venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="venv/Scripts/python.exe"
fi

export CIPM_MOCK="${CIPM_MOCK:-1}"
"$PYTHON_BIN" -m mock.cli --write
exec "$PYTHON_BIN" ops/start_dev.py "$@"
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ -x "venv/bin/python" ]; then
  PYTHON_BIN="venv/bin/python"
elif [ -x "venv/Scripts/python.exe" ]; then
  PYTHON_BIN="venv/Scripts/python.exe"
else
  BASE_PYTHON=""
  if command -v python3.12 >/dev/null 2>&1; then
    BASE_PYTHON="python3.12"
  elif command -v python3 >/dev/null 2>&1 && python3 -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >/dev/null 2>&1; then
    BASE_PYTHON="python3"
  fi
  if [ -z "$BASE_PYTHON" ]; then
    echo "[ERROR] Python 3.12 is required but was not found (need python3.12, or python3 == 3.12.x)." >&2
    exit 1
  fi
  echo "[INFO] venv not found, creating virtualenv with $BASE_PYTHON ..."
  "$BASE_PYTHON" -m venv venv
  if [ -x "venv/bin/python" ]; then
    PYTHON_BIN="venv/bin/python"
  else
    PYTHON_BIN="venv/Scripts/python.exe"
  fi
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -e ".[ui]"
fi

export CIPM_MOCK="${CIPM_MOCK:-1}"
export CIPM_RUNTIME="${CIPM_RUNTIME:-local}"
"$PYTHON_BIN" -m mock.cli --write
exec "$PYTHON_BIN" ops/start_dev.py "$@"
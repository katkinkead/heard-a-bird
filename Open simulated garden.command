#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys, sqlite3, zoneinfo; assert sys.version_info >= (3,9)' 2>/dev/null; then
  echo 'The simulated garden needs Python 3.9 or newer from python.org.'
  read -r -p 'Press Return to close this window. ' reply
  exit 1
fi
python3 scripts/simulate.py

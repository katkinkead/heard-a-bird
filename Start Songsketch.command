#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys, sqlite3, zoneinfo; assert sys.version_info >= (3,9)' 2>/dev/null; then
  echo 'One small ingredient is missing: Python 3.9 or newer.'
  echo 'Install Python from python.org, then open this file again.'
  open 'https://www.python.org/downloads/macos/'
  read -r -p 'Press Return to close this window. ' reply
  exit 1
fi
python3 scripts/start.py

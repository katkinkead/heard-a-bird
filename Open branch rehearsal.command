#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
branch_python=python3
# Reuse this workspace's existing solar runtime, without installing anything.
if [ -x ../../work/solar-proof/venv/bin/python ]; then
  branch_python=../../work/solar-proof/venv/bin/python
fi
if ! "$branch_python" -c 'import sys, sqlite3, zoneinfo; assert sys.version_info >= (3,9)' 2>/dev/null; then
  echo 'The branch rehearsal needs Python 3.9 or newer from python.org.'
  read -r -p 'Press Return to close. ' reply
  exit 1
fi
if [ -d ../../work/branch-rehearsal ]; then
  branch_data="$(cd ../../work/branch-rehearsal && pwd)"
else
  branch_data="$HOME/Library/Application Support/Songsketch Branch Rehearsal"
fi
exec "$branch_python" scripts/simulate.py --branch --port 8772 --data-dir "$branch_data"

#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
python3 scripts/install-mac-service.py
read -r -p 'Press Return to close this window. ' reply

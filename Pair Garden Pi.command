#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
bash scripts/pair-pi.sh
read -r -p 'Press Return to close this window. ' reply

#!/usr/bin/env bash
# Interactive SSH handover; no passwords/tokens in process arguments or logs.
set -euo pipefail
umask 077
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PACKAGE_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
if [[ ${1:-} == --help ]]; then
  echo 'Usage: scripts/pair-pi.sh [--check]'
  echo 'Prompts for the Pi SSH account/address and the server LAN URL; uses local station credentials.'
  exit 0
fi
CHECK_ONLY=0
[[ ${1:-} != --check ]] || CHECK_ONLY=1
for tool in ssh scp tar python3; do
  command -v "$tool" >/dev/null || { echo "Missing $tool. Install/start Songsketch first." >&2; exit 2; }
done
echo 'Use the Pi account and hostname set in Raspberry Pi first-boot setup or Imager.'
echo 'For a first SSH connection, compare the host-key fingerprint with the Pi before accepting it.'
read -r -p 'Pi SSH address (e.g. garden@raspberrypi.local): ' PI_TARGET
[[ "$PI_TARGET" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]*@[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]] || { echo 'Enter username@hostname or username@IPv4-address; no spaces or options.' >&2; exit 2; }
echo 'Checking the Pi connection. SSH may ask for its password or host-key confirmation.'
ssh -o StrictHostKeyChecking=ask -o ConnectTimeout=10 "$PI_TARGET" 'uname -m; cat /etc/os-release; test -d /dev/snd && echo "ALSA device present; this does not yet prove microphone capture" || echo "Connect the USB microphone"'
if [[ "$CHECK_ONLY" == 1 ]]; then
  echo 'Connection checked. No files or settings changed on the Pi.'; exit 0
fi
DEFAULT_ADDRESS=''
if [[ $(uname -s) == Darwin ]]; then
  DEFAULT_ADDRESS=$(ipconfig getifaddr en0 2>/dev/null || true)
  [[ -n "$DEFAULT_ADDRESS" ]] || DEFAULT_ADDRESS=$(ipconfig getifaddr en1 2>/dev/null || true)
elif command -v hostname >/dev/null; then
  DEFAULT_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
fi
DEFAULT_URL="http://${DEFAULT_ADDRESS:-SERVER-LAN-ADDRESS}:8765"
read -r -p "Songsketch server LAN URL [$DEFAULT_URL]: " SERVER_URL
SERVER_URL=${SERVER_URL:-$DEFAULT_URL}
export SERVER_URL
TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/songsketch-pair.XXXXXXXX")
REMOTE_DIR=''
cleanup() {
  rm -rf -- "$TEMP_DIR"
  if [[ -n "$REMOTE_DIR" ]]; then
    ssh -o BatchMode=yes -o ConnectTimeout=5 "$PI_TARGET" "rm -rf -- '$REMOTE_DIR'" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
export TEMP_DIR PACKAGE_DIR
python3 - <<'PY'
import importlib.util,json,os,sys
from pathlib import Path
sys.path.insert(0,os.environ['PACKAGE_DIR'])
from songsketch.config import data_directory
base=data_directory();secret=base/'secrets.json';config=base/'config.json'
if not secret.exists():raise SystemExit('Start Songsketch on this computer first; it creates the private station credentials.')
if secret.stat().st_mode & 0o077:raise SystemExit('Local secrets.json must be owner-only (mode 600).')
spec=importlib.util.spec_from_file_location('relay',Path(os.environ['PACKAGE_DIR'])/'pi/relay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
url=m.validate_url(os.environ['SERVER_URL'])
from urllib.parse import urlsplit
if urlsplit(url).hostname in ('localhost','127.0.0.1','::1','SERVER-LAN-ADDRESS'):
    raise SystemExit('Use the Mac/server LAN address, not localhost: the Pi must reach this computer.')
settings=json.loads(config.read_text()) if config.exists() else {}
token=json.loads(secret.read_text())['station_token']
target=Path(os.environ['TEMP_DIR'])/'provision.json'
target.write_text(json.dumps({'server_url':url,'station_id':settings.get('station_id','garden'),'token':token}))
target.chmod(0o600)
PY
unset SERVER_URL
echo 'This installs Songsketch and Docker if needed on the Pi, downloads BirdNET-Go 20261014,'
echo 'preserves existing history/settings, and registers automatic startup services. No SD-card flashing.'
read -r -p 'Continue with this Pi? [y/N]: ' CONTINUE
[[ "$CONTINUE" == y || "$CONTINUE" == Y ]] || { echo 'No installation performed.'; exit 0; }
read -r -p 'Use an existing BirdNET-Go installation on this Pi? [y/N]: ' USE_EXISTING
EXTRA=''
[[ "$USE_EXISTING" != y && "$USE_EXISTING" != Y ]] || EXTRA='--skip-birdnet'
REMOTE_DIR=$(ssh -o StrictHostKeyChecking=ask -o ConnectTimeout=10 "$PI_TARGET" 'umask 077; mktemp -d /tmp/songsketch-pair.XXXXXXXX')
[[ "$REMOTE_DIR" =~ ^/tmp/songsketch-pair\.[a-zA-Z0-9]+$ ]] || { echo 'Unexpected Pi staging directory.' >&2; REMOTE_DIR=''; exit 2; }
tar --exclude='__pycache__' --exclude='*.pyc' -czf "$TEMP_DIR/pi-package.tar.gz" -C "$PACKAGE_DIR" pi scripts/install-pi.sh scripts/install-linux-service.sh
scp -o StrictHostKeyChecking=ask "$TEMP_DIR/pi-package.tar.gz" "$TEMP_DIR/provision.json" "$PI_TARGET:$REMOTE_DIR/"
ssh -tt -o StrictHostKeyChecking=ask "$PI_TARGET" "chmod 600 '$REMOTE_DIR/provision.json'; tar -xzf '$REMOTE_DIR/pi-package.tar.gz' -C '$REMOTE_DIR'; sudo bash '$REMOTE_DIR/scripts/install-pi.sh' --provision '$REMOTE_DIR/provision.json' $EXTRA; code=\$?; rm -f '$REMOTE_DIR/provision.json'; exit \$code"
echo 'Pi software installation finished. The next step checks the real microphone and recognition.'
echo 'The helper can open an SSH tunnel: BirdNET http://localhost:18080 and Pi health http://localhost:18081/health.'
echo 'Keep this Terminal window open while completing the BirdNET setup wizard. Close with Ctrl-C.'
read -r -p 'Open the setup tunnel now? [Y/n]: ' TUNNEL
if [[ "$TUNNEL" != n && "$TUNNEL" != N ]]; then
  if [[ $(uname -s) == Darwin ]]; then
    (sleep 2; open 'http://localhost:18080') &
  fi
  ssh -o StrictHostKeyChecking=ask -o ExitOnForwardFailure=yes -L 127.0.0.1:18080:127.0.0.1:8080 -L 127.0.0.1:18081:127.0.0.1:8081 -N "$PI_TARGET"
fi

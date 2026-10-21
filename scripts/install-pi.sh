#!/usr/bin/env bash
# No remote shell bootstrap: this script ships in the same release as the relay.
set -euo pipefail
umask 077
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PACKAGE_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CHECK_ONLY=0
SKIP_BIRDNET=0
PROVISION=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) CHECK_ONLY=1; shift ;;
    --skip-birdnet) SKIP_BIRDNET=1; shift ;;
    --provision) PROVISION=${2:?Provide a private provisioning JSON file}; shift 2 ;;
    --help) echo 'Usage: sudo scripts/install-pi.sh [--check] [--skip-birdnet] [--provision PRIVATE_FILE]'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]] || { echo 'This installer requires a 64-bit Raspberry Pi OS installation (aarch64).' >&2; exit 2; }
[[ -r /etc/os-release ]] || { echo 'Cannot identify the installed OS.' >&2; exit 2; }
# The OS file is local operating-system configuration.
source /etc/os-release
[[ ${ID:-} == debian || ${ID:-} == raspbian ]] || { echo 'Supported: Raspberry Pi OS based on Debian Bookworm or Trixie.' >&2; exit 2; }
[[ ${VERSION_ID:-} == 12 || ${VERSION_ID:-} == 13 ]] || { echo 'Supported OS versions: Debian/Raspberry Pi OS 12 or 13, 64-bit.' >&2; exit 2; }
command -v dpkg >/dev/null && [[ $(dpkg --print-architecture) == arm64 ]] || { echo '64-bit arm64 userspace is required; a 64-bit kernel with a 32-bit OS is not supported.' >&2; exit 2; }
[[ -r /proc/device-tree/model ]] && grep -q 'Raspberry Pi' /proc/device-tree/model || { echo 'This installer is for Raspberry Pi hardware.' >&2; exit 2; }
command -v systemctl >/dev/null || { echo 'systemd is required.' >&2; exit 2; }
has_capture_device() {
  local device
  for device in /dev/snd/pcm*C*c; do
    [[ -c "$device" ]] && return 0
  done
  return 1
}
if [[ "$CHECK_ONLY" == 1 ]]; then
  if [[ "$SKIP_BIRDNET" == 1 ]]; then
    echo 'Platform check passed. Would install the Songsketch relay while retaining the existing BirdNET installation.'
  else
    echo 'Platform check passed. Would install Python 3, Docker if needed, pinned BirdNET-Go 20261014 and Songsketch relay once capture is available.'
  fi
  echo 'Existing databases, microphone settings and credentials are preserved. No changes made.'
  if has_capture_device; then
    echo 'ALSA capture device present. Actual input signal, microphone power and BirdNET analysis still require testing.'
  else
    echo 'No ALSA capture device found. Connect the USB microphone/audio interface before fresh BirdNET installation; HDMI playback does not count.'
    [[ "$SKIP_BIRDNET" == 0 ]] || echo 'Existing BirdNET route selected; verify its audio source separately.'
  fi
  exit 0
fi
[[ $(id -u) == 0 ]] || { echo 'Run this installer with sudo.' >&2; exit 2; }
if [[ "$SKIP_BIRDNET" == 0 ]] && ! has_capture_device; then
  echo 'No ALSA capture device found. Connect the USB microphone/audio interface and retry; HDMI playback alone is not sufficient. No device has been erased.' >&2; exit 2
fi
if ! command -v python3 >/dev/null || { [[ "$SKIP_BIRDNET" == 0 ]] && ! command -v docker >/dev/null; }; then
  apt-get update
  packages=(python3 ca-certificates tzdata)
  [[ "$SKIP_BIRDNET" == 1 ]] || packages+=(docker.io)
  apt-get install -y "${packages[@]}"
fi
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11 or later is required"'
id songsketch-pi >/dev/null 2>&1 || useradd --system --home /var/lib/songsketch-pi --shell /usr/sbin/nologin songsketch-pi
install -d -m 0755 /opt/songsketch-pi
install -d -m 0750 -o root -g songsketch-pi /etc/songsketch-pi
install -d -m 0700 -o songsketch-pi -g songsketch-pi /var/lib/songsketch-pi
install -m 0644 "$PACKAGE_DIR/pi/relay.py" /opt/songsketch-pi/relay.py
if [[ -z "$PROVISION" && ! -f /etc/songsketch-pi/config.json ]]; then
  echo 'Enter the Songsketch server address shown on the Mac setup page, e.g. http://192.168.1.20:8765'
  read -r -p 'Server URL: ' SERVER_URL
  read -r -s -p 'Station token (input hidden): ' STATION_TOKEN; echo
  PROVISION=$(mktemp /tmp/songsketch-provision.XXXXXXXX)
  export SERVER_URL STATION_TOKEN PROVISION
  python3 - <<'PY'
import os,json
with open(os.environ['PROVISION'],'w') as f:
    json.dump({'server_url':os.environ['SERVER_URL'],'station_id':'garden','token':os.environ['STATION_TOKEN']},f)
PY
  unset STATION_TOKEN SERVER_URL
  trap 'rm -f -- "$PROVISION"' EXIT
fi
python3 - "$PROVISION" <<'PY'
import importlib.util,json,os,pwd,re,sys,uuid
from pathlib import Path
spec=importlib.util.spec_from_file_location('relay','/opt/songsketch-pi/relay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=Path('/etc/songsketch-pi');p=base/'config.json'
config=json.loads(p.read_text()) if p.exists() else {}
if sys.argv[1]:
    source=Path(sys.argv[1])
    if source.stat().st_mode & 0o077: raise SystemExit('Provisioning file must have mode 600.')
    new=json.loads(source.read_text())
    server=m.validate_url(new['server_url']);station=new.get('station_id','garden');token=new['token']
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',station): raise SystemExit('Invalid station ID.')
    if len(token)<24 or any(c in token for c in '\r\n'): raise SystemExit('Invalid station token.')
    from zoneinfo import ZoneInfo
    zone=new.get('timezone',config.get('timezone','Europe/London'));ZoneInfo(zone)
    config.update(server_url=server,station_id=station,timezone=zone)
    target=base/'station.token';target.write_text(token+'\n');target.chmod(0o600)
config.setdefault('source_instance_id',str(uuid.uuid4()))
config.setdefault('birdnet_url','http://127.0.0.1:8080')
config.setdefault('timezone','Europe/London')
config.setdefault('model_id','BirdNET_V2.4')
config.setdefault('token_file','/etc/songsketch-pi/station.token')
config.setdefault('data_dir','/var/lib/songsketch-pi')
config.setdefault('listen_host','127.0.0.1')
config.setdefault('listen_port',8081)
temporary=p.with_suffix('.tmp');temporary.write_text(json.dumps(config,indent=2)+'\n');temporary.chmod(0o600)
m.load_config(temporary);m.read_secret(config['token_file'])
temporary.replace(p)
u=pwd.getpwnam('songsketch-pi')
for target in (p,base/'station.token'):os.chown(target,u.pw_uid,u.pw_gid)
PY
if [[ "$SKIP_BIRDNET" == 0 ]]; then
  BIRD_TIMEZONE=$(python3 -c "import json;print(json.load(open('/etc/songsketch-pi/config.json'))['timezone'])")
  systemctl enable --now docker
  if docker container inspect songsketch-birdnet >/dev/null 2>&1; then
    managed=$(docker inspect --format '{{index .Config.Labels "org.songsketch.managed"}}' songsketch-birdnet)
    [[ "$managed" == true ]] || { echo 'An unmanaged container already uses songsketch-birdnet; refusing to replace it.' >&2; exit 2; }
    docker start songsketch-birdnet >/dev/null
  else
    if command -v ss >/dev/null && ss -ltn | grep -Eq ':8080[[:space:]]'; then
      echo 'Port 8080 is already occupied. To use an existing BirdNET installation, rerun with --skip-birdnet.' >&2; exit 2
    fi
    RELEASE_IMAGE='ghcr.io/tphakala/birdnet-go:20261014'
    LOCK=/etc/songsketch-pi/birdnet-image.lock
    if [[ -s "$LOCK" ]]; then
      PINNED_IMAGE=$(cat "$LOCK")
      [[ "$PINNED_IMAGE" =~ ^ghcr.io/tphakala/birdnet-go@sha256:[a-f0-9]{64}$ ]] || { echo 'Invalid stored container digest.' >&2; exit 2; }
      docker pull "$PINNED_IMAGE"
    else
      docker pull --platform linux/arm64 "$RELEASE_IMAGE"
      PINNED_IMAGE=$(docker image inspect --format '{{index .RepoDigests 0}}' "$RELEASE_IMAGE")
      [[ "$PINNED_IMAGE" =~ ^ghcr.io/tphakala/birdnet-go@sha256:[a-f0-9]{64}$ ]] || { echo 'Could not verify the downloaded container digest.' >&2; exit 2; }
      printf '%s\n' "$PINNED_IMAGE" > "$LOCK"
      chmod 0600 "$LOCK"
    fi
    install -d -m 0700 /var/lib/songsketch-birdnet/config /var/lib/songsketch-birdnet/data
    BIRD_UID=$(id -u songsketch-pi)
    BIRD_GID=$(id -g songsketch-pi)
    chown -R "$BIRD_UID:$BIRD_GID" /var/lib/songsketch-birdnet
    docker run -d --name songsketch-birdnet --restart unless-stopped \
      --label org.songsketch.managed=true --label org.songsketch.birdnet-release=20261014 \
      --publish 127.0.0.1:8080:8080 --device /dev/snd:/dev/snd \
      --env "TZ=$BIRD_TIMEZONE" --env BIRDNET_LOCALE=en-uk \
      --env "BIRDNET_UID=$BIRD_UID" --env "BIRDNET_GID=$BIRD_GID" \
      --volume /var/lib/songsketch-birdnet/config:/config \
      --volume /var/lib/songsketch-birdnet/data:/data \
      --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
      "$PINNED_IMAGE" >/dev/null
  fi
fi
bash "$SCRIPT_DIR/install-linux-service.sh"
echo 'Software installed. Finish BirdNET microphone and Dorset location setup through the SSH tunnel.'
echo 'Then check: sudo -u songsketch-pi python3 /opt/songsketch-pi/relay.py --check'
echo 'Installation does not establish a verified real microphone/detection test.'

#!/usr/bin/env bash
# Dedicated Ubuntu/Debian-style Linux mini PC. This is not the garden Pi installer.
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PACKAGE_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
if [[ ${1:-} == --check ]]; then
  command -v systemctl >/dev/null || { echo 'This profile requires Linux with systemd.'; exit 2; }
  python3 -c 'import sys, sqlite3, zoneinfo; assert sys.version_info >= (3,9)'
  echo 'Would install Songsketch server in /opt/songsketch-server, data in /var/lib/songsketch-server.'
  exit 0
fi
[[ $(uname -s) == Linux ]] || { echo 'Use the Mac launcher on macOS.'; exit 2; }
[[ $(id -u) == 0 ]] || { echo 'Run with sudo on the dedicated Linux mini PC.'; exit 2; }
command -v systemctl >/dev/null || { echo 'systemd is required.'; exit 2; }
python3 -c 'import sys, sqlite3, zoneinfo; assert sys.version_info >= (3,9)'
id songsketch >/dev/null 2>&1 || useradd --system --home /var/lib/songsketch-server --shell /usr/sbin/nologin songsketch
install -d -m 755 /opt/songsketch-server
install -d -o songsketch -g songsketch -m 700 /var/lib/songsketch-server
# Only tracked application directories; never copy an operator's data or credentials.
for name in songsketch static guide artwork scripts pi docs; do
  cp -R "$PACKAGE_DIR/$name" /opt/songsketch-server/
done
cp "$PACKAGE_DIR/README.md" "$PACKAGE_DIR/AGENTS.md" "$PACKAGE_DIR/CLAUDE.md" /opt/songsketch-server/
chown -R root:root /opt/songsketch-server
chmod -R go-w /opt/songsketch-server
cat > /etc/systemd/system/songsketch-server.service <<'SERVICE'
[Unit]
Description=Songsketch bird paintings and garden history
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
User=songsketch
Group=songsketch
WorkingDirectory=/opt/songsketch-server
Environment=SONGSKETCH_DATA_DIR=/var/lib/songsketch-server
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 -m songsketch.supervisor
Restart=on-failure
RestartPreventExitStatus=3 4
RestartSec=20
TimeoutStopSec=40
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/songsketch-server
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable --now songsketch-server
echo 'Server service installed. Check: sudo systemctl status songsketch-server'
echo 'On the mini PC open http://localhost:8765/setup. For remote admin, use an SSH localhost tunnel.'
echo 'Private setup code: sudo python3 -c '\''import json; print(json.load(open("/var/lib/songsketch-server/secrets.json"))["admin_token"])'\'''
echo 'Complete docs/production.md before leaving this installation unattended.'

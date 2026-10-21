#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} == --help ]]; then
  echo 'Usage: sudo scripts/install-linux-service.sh [--check]'; exit 0
fi
if [[ ${1:-} == --check ]]; then
  command -v systemctl >/dev/null || { echo 'systemd is required.' >&2; exit 2; }
  echo 'Would install songsketch-pi.service; no changes made.'; exit 0
fi
[[ $(id -u) == 0 ]] || { echo 'Run with sudo after install-pi.sh.' >&2; exit 2; }
[[ -f /opt/songsketch-pi/relay.py && -f /etc/songsketch-pi/config.json ]] || { echo 'Install the Pi package first.' >&2; exit 2; }
cat > /etc/systemd/system/songsketch-pi.service <<'SERVICE'
[Unit]
Description=Songsketch garden Pi detection and maintenance relay
Wants=network-online.target
After=network-online.target docker.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=songsketch-pi
Group=songsketch-pi
WorkingDirectory=/var/lib/songsketch-pi
ExecStart=/usr/bin/python3 /opt/songsketch-pi/relay.py --config /etc/songsketch-pi/config.json
Restart=on-failure
RestartSec=15
TimeoutStopSec=40
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/songsketch-pi
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable songsketch-pi.service
if [[ ${SONGSKETCH_DEFER_RELAY_START:-0} == 1 ]]; then
  systemctl stop songsketch-pi.service
  echo 'Songsketch Pi service installed; commissioning will start it after BirdNET settings and live analysis are verified.'
else
  systemctl restart songsketch-pi.service
  echo 'Songsketch Pi service installed. Check: sudo systemctl status songsketch-pi'
fi

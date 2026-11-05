#!/usr/bin/env bash
# Run on the already-installed dedicated VPS. Separate disposable QA runtime.
set -euo pipefail
umask 077
DOMAIN=${1:?Supply a QA hostname}; RUN_DIR=${2:?Supply a fresh absolute run directory}
[[ $DOMAIN =~ ^[a-z0-9.-]+$ && $DOMAIN == *.* && $RUN_DIR == /var/lib/heardabirdy-qa/run-* ]] || exit 2
[[ $(id -u) == 0 && ! -e $RUN_DIR ]] || { echo 'Root and a fresh run directory required'; exit 2; }
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
[[ -f /etc/caddy/Caddyfile && ! -e /etc/systemd/system/heardabirdy-qa.service ]] || { echo 'Review existing QA deployment before replacing it'; exit 2; }
install -d -o songsketch -g songsketch -m 0711 /var/lib/heardabirdy-qa "$RUN_DIR"
install -d -o songsketch -g songsketch -m 0755 "$RUN_DIR/evidence"
cat > /etc/systemd/system/heardabirdy-qa.service <<UNIT
[Unit]
Description=Heard a Birdy bounded synthetic cloud QA
After=network-online.target caddy.service
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=3
[Service]
User=songsketch
Group=songsketch
WorkingDirectory=$ROOT
Environment=PLAYWRIGHT_BROWSERS_PATH=/opt/heardabirdy-qa-browsers
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/heardabirdy-qa-venv/bin/python $ROOT/scripts/qa-cloud.py --run-dir $RUN_DIR --public-url https://$DOMAIN --duration-hours 24
Restart=on-failure
RestartSec=20
MemoryMax=1300M
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
UNIT
cp -a /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.before-qa-$(date +%Y%m%dT%H%M%S)"
cat > /etc/caddy/heardabirdy-qa.caddy <<CADDY
$DOMAIN {
    encode gzip
    header X-Robots-Tag "noindex, nofollow"
    request_body {
        max_size 1MB
    }
    handle /qa-marker.json {
        root * $RUN_DIR/evidence
        file_server
    }
    handle_path /evidence/* {
        root * $RUN_DIR/evidence
        file_server
    }
    @display path / /branch /events /health /status /api/public/status /api/catalogue /api/branch/state /api/branch/catalogue /api/display/session /api/display/reports /api/ingest/detections /api/ingest/heartbeat /api/ingest/reports /static/* /artwork/* /approved-artwork/*
    handle @display {
        reverse_proxy 127.0.0.1:8768 {
            header_up Host $DOMAIN
            flush_interval -1
        }
    }
    handle {
        respond "Not found" 404
    }
}
CADDY
chmod 644 /etc/caddy/heardabirdy-qa.caddy
printf '\nimport /etc/caddy/heardabirdy-qa.caddy\n' >> /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
install -d /etc/systemd/system/caddy.service.d
printf '[Service]\nRestart=on-failure\nRestartSec=5\n' > /etc/systemd/system/caddy.service.d/20-recovery.conf
systemctl daemon-reload
systemctl restart caddy
systemctl is-active --quiet caddy
systemctl daemon-reload
systemctl enable --now heardabirdy-qa
echo "QA status: https://$DOMAIN/evidence/"
echo 'Transfer station-config.json privately to the Pi; never commit or print it.'

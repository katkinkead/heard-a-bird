#!/usr/bin/env bash
# Dedicated Debian/Ubuntu VPS: same application, private admin, HTTPS display/ingress.
set -euo pipefail
umask 077
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DOMAIN=${1:-}
[[ "$DOMAIN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ && "$DOMAIN" == *.* && "$DOMAIN" != *..* ]] || { echo 'Usage: sudo scripts/install-vps.sh public.hostname [--check]'; exit 2; }
if [[ ${2:-} == --check ]]; then
  echo "Plan: existing Linux server installer; bind 127.0.0.1:8765; Caddy HTTPS for $DOMAIN; UFW SSH/HTTP/HTTPS only."
  echo 'Public display and token-protected station ingestion only; operator access through SSH forwarding.'
  exit 0
fi
[[ $(id -u) == 0 && $(uname -s) == Linux ]] || { echo 'Run with sudo on the dedicated Linux VPS.'; exit 2; }
command -v systemctl >/dev/null
# Never replace an unrelated reverse proxy or silently change domains.
if command -v caddy >/dev/null && [[ -f /etc/caddy/Caddyfile ]]; then
  grep -q '^# Managed by Songsketch VPS installer$' /etc/caddy/Caddyfile || { echo 'Existing Caddy configuration requires review; left untouched.'; exit 2; }
  grep -qxF "$DOMAIN {" /etc/caddy/Caddyfile || { echo 'Existing hostname differs; review migration first.'; exit 2; }
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y caddy ufw
install -d -m 0755 /etc/systemd/system/songsketch-server.service.d
cat > /etc/systemd/system/songsketch-server.service.d/20-vps.conf <<'UNIT'
[Service]
ExecStart=
ExecStart=/usr/bin/python3 -m songsketch.supervisor --host 127.0.0.1
UNIT
bash "$ROOT/scripts/install-server-linux.sh"
# Keep an on-host rollback copy of the default/previous proxy config.
cp -a /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.before-songsketch-$(date +%Y%m%dT%H%M%S)"
cat > /etc/caddy/Caddyfile <<CADDY
# Managed by Songsketch VPS installer
$DOMAIN {
    encode zstd gzip
    header X-Robots-Tag "noindex, nofollow"
    request_body {
        max_size 1MB
    }
    @public path / /display /branch /events /health /status /api/public/status /api/catalogue /api/branch/state /api/branch/catalogue /api/display/session /api/display/reports /api/ingest/detections /api/ingest/heartbeat /api/ingest/reports /detections /heartbeat /debug-reports /static/* /artwork/* /approved-artwork/*
    handle @public {
        reverse_proxy 127.0.0.1:8765 {
            header_up Host $DOMAIN
            flush_interval -1
        }
    }
    handle {
        respond "Not found" 404
    }
}
CADDY
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
systemctl daemon-reload
systemctl restart songsketch-server
systemctl enable --now caddy
systemctl reload caddy
printf 'Application deployed; verify HTTPS issuance and route tests at https://%s before commissioning the Pi.\n' "$DOMAIN"
echo 'Admin: SSH forward a free local port to VPS 127.0.0.1:8765, then use the private setup guide.'

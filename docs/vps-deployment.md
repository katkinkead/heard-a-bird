# VPS deployment

This deployment retains the same architecture: **BirdNET-Go on the garden Pi → authenticated detection/heartbeat delivery → Songsketch server → browser painting**. The Mac is only a setup/admin workstation. No recognition or AI API key is required on the VPS.

The existing dedicated Linux installer remains the application/service installer. `scripts/install-vps.sh HOSTNAME` adds a systemd override binding it to loopback, Caddy automatic HTTPS, and a UFW firewall for SSH/HTTP/HTTPS. Run it on a fresh dedicated Debian/Ubuntu VPS after uploading the complete release. Do not run it on an existing shared host without reviewing its services and firewall. The script refuses to replace unrelated Caddy settings.

```sh
sudo bash scripts/install-vps.sh heardabirdy.example.com --check
sudo bash scripts/install-vps.sh heardabirdy.example.com
```

Use a hostname resolving to the VPS. For temporary staging, sslip.io can resolve a name such as `heardabirdy.157-180-70-10.sslip.io` without buying a domain. This depends on a third-party DNS service and certificate issuance; use an owned domain for the permanent installation. Caddy manages TLS issuance and renewal. DNS must resolve correctly and ports 80/443 must be reachable.

Public access is deliberately limited to the display, its assets/status/SSE, bounded browser fault reporting, and the existing token-protected station ingress endpoints. Setup, dashboard, debug, documentation, scripts and admin APIs are not forwarded. The proxy fixes the upstream Host to the public hostname so the backend cannot mistake a forwarded request for local administration. The backend port 8765 is loopback-only and must not be opened in the firewall. The painting/history summary is publicly readable: this is not a private viewer login system.

Administration uses an SSH loopback tunnel:

```sh
ssh -L 127.0.0.1:18765:127.0.0.1:8765 admin@VPS
```

Open `http://127.0.0.1:18765/setup` and unlock privately using the server's existing operator credential. Never put that credential in chat, a public URL, repository, or the Pi station-token field. Service/data locations remain `/opt/songsketch-server` and `/var/lib/songsketch-server`; migration and rollback use the existing production procedures. VPS disk backups complement, rather than replace, application SQLite backups.

Provision the Pi relay with the actual **HTTPS** server URL and its station token through protected SSH input. BirdNET remains on Pi loopback; do not publish its management port. Recognition needs the real microphone and exact garden coordinates. Without a microphone, Docker and the pinned BirdNET image can be prepared, but capture/inference/real-bird commissioning must stay pending. Dorset is the intended location; do not invent coordinates from the county name.

Before handover, verify TLS, `/health`, display assets/SSE, rejection of public admin routes and unauthenticated ingestion, an authenticated labelled test detection, restart recovery, and Pi heartbeat delivery. A synthetic test does not establish live audio capture. Save the checked release commit, server details and remaining checks without secrets.

References: [Caddy HTTPS](https://caddyserver.com/docs/automatic-https), [reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [sslip.io](https://sslip.io/).

## Deployment verification — 5 November 2026

Verified on a fresh Hetzner CPX12 running Debian 13: the systemd application starts as its dedicated unprivileged user; Caddy serves valid HTTPS; `/health`, `/` and `/branch` return 200. Public setup, dashboard, documentation and admin endpoints return 404; unauthenticated station ingestion returns 401. A labelled Robin test was accepted and the browser loaded its painting player without console errors. The physical Pi 4 then sent a labelled Robin detection and an audio/inference-unknown heartbeat over HTTPS, both accepted with 200.

The Linux installer now normalizes public code permissions before checking import as the service user. This fixes deployment under a restrictive umask without changing the private runtime directory's permissions.

These checks establish deployment and authenticated Pi delivery, not live recognition. No microphone was connected. Exact garden coordinates, microphone capture, BirdNET inference, persistent relay commissioning and physical reboot/reconnect tests remain pending. The webpage can therefore show a disconnected Pi after the one-off test heartbeat expires.

For the separate physical-Pi/cloud-browser soak, see [cloud QA](cloud-qa.md).

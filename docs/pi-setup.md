# Garden Pi setup and verification

The Pi runs BirdNET-Go for recognition and the Songsketch relay for delivery, health and reports. Recognition and ordinary painting playback need no AI API key. This implementation is tested against mocked BirdNET APIs and server failures; installation, audio capture and reboot recovery still require the actual Pi and microphone. Do not describe those physical checks as passed.

## The short setup route

1. Check the supplied SD card. Reuse supported **64-bit Raspberry Pi OS Bookworm (Debian 12) or Trixie (Debian 13)**. The installer checks `aarch64`, the OS release and the Raspberry Pi hardware marker. It does not flash or erase the card. First-boot account, Wi-Fi/Ethernet and SSH setup are human steps.
2. Connect the USB microphone so `/dev/snd` exists. Start Songsketch on the MacBook first. Keep it awake, with its firewall allowing the Songsketch server on the trusted home network.
3. Open **Pair Garden Pi.command**, or run `bash scripts/pair-pi.sh` from this release. Enter the Pi SSH account/address and the server's LAN URL. A Pi must use the Mac's LAN address, for example `http://192.168.1.20:8765`, never `localhost`. Compare the SSH host-key fingerprint before accepting a new host. The helper does not disable host verification.
4. The helper transfers this release's relay and installer over SSH, together with the station token already created by the local server. The token is not printed or placed in command arguments. Confirm the intended Pi; the installer uses `sudo` on it. Software download needs internet on first installation.
5. Accept the setup tunnel. BirdNET opens at **http://localhost:18080** on the Mac. Complete its wizard: select the actual USB microphone, set the garden's location and Europe/London timezone, and use **BirdNET v2.4** for this tested species contract. Do not guess a microphone device name. The container's UI is bound to Pi loopback; keep the SSH tunnel open during setup.
6. Check Songsketch's dashboard. A connected Pi with **listening unknown** means the health evidence has not yet established successful capture and recognition; it is not a healthy-listening result. Verify a real recorded detection and the correct artwork after the clearly labelled simulation test.

The helper also tunnels the Pi's minimal health endpoint to **http://localhost:18081/health**. A successful result proves only that the relay's local HTTP process answers. It deliberately does not certify audio or inference.

`bash scripts/pair-pi.sh --check` performs a connection/device inventory without installing. On the Pi, `sudo bash scripts/install-pi.sh --check` checks the supported platform without changes. `sudo bash scripts/install-pi.sh --skip-birdnet` installs the relay while retaining an existing BirdNET installation; verify that installation's version and API access separately.

## What the installer changes

| Location | Purpose |
|---|---|
| `/opt/songsketch-pi/relay.py` | Release-managed relay code; replaced on a repeat install |
| `/etc/songsketch-pi/config.json` | Station/server settings and persistent BirdNET database identity |
| `/etc/songsketch-pi/station.token` | Owner-only station credential |
| `/etc/songsketch-pi/birdnet-image.lock` | Resolved immutable container digest from release 20261014 |
| `/var/lib/songsketch-pi/` | Durable SQLite outbox, scan checkpoint, reports, rolling logs and three daily backups |
| `/var/lib/songsketch-birdnet/` | BirdNET settings, recognition database, models and any locally configured audio clips |
| `songsketch-pi.service` | Unprivileged relay startup and bounded crash restarts |
| `songsketch-birdnet` | Managed Docker container with restart policy and bounded Docker logs |

Installation preserves existing history and configuration. If Docker is missing it installs the OS `docker.io` package; it does not run a downloaded shell bootstrap. It pulls `ghcr.io/tphakala/birdnet-go:20261014`, records the registry content digest and runs that immutable digest. Repeat installation uses the lock and leaves an existing managed container intact; it does not silently upgrade BirdNET. Do not edit the image lock as an update strategy. Actual first-time image download and Pi execution remain hardware verification steps.

An unrelated service already on port 8080 or a container with the expected name but without Songsketch's ownership label is left in place and installation stops with a concrete message. Use the existing-installation route deliberately rather than overwriting it.

## Delivery and counting

The relay reads **stored detections** using `/api/v2/detections` with `start_date`, `end_date`, `sortBy=date_asc`, `numResults` and `offset`. It does not depend on MQTT or a transient notification stream. Each detection is normalized to the receiver contract and committed to a SQLite outbox before delivery. Marking a record seen and queueing it happen in the same transaction.

The event identity is `birdnet:<source_instance_id>:<BirdNET database record id>`. Retries keep the same identity. The server acknowledges only after its own commit; losing an acknowledgement safely causes the same event to be retried. Network failures back off up to five minutes without deleting pending events. This prevents delivery retries from increasing bird counts.

The first installation imports the last 30 days by default. A completed day's checkpoint is persisted only after all its pages have been queued. Every later scan overlaps the previous day and catches up to today after a relay outage. The overlap handles ordinary pagination movement and recent late entries. Catch-up is limited by BirdNET's retained database history. Pending relay records and reports survive restarts, but storage is finite; low disk space pauses history collection without advancing its checkpoint and creates a fault report when the database is still writable.

Already-delivered detections subsequently deleted or marked false-positive in BirdNET are **not currently retracted from Songsketch**. Future imports dated earlier than the overlap need a deliberate rescan. The app records accepted detections, not a known count of individual birds or visits.

To rescan retained BirdNET history without deleting deduplication records, stop the relay, run the following on the Pi, and restart it:

```sh
sudo systemctl stop songsketch-pi
sudo -u songsketch-pi python3 /opt/songsketch-pi/relay.py --rescan-from 2026-10-01
sudo systemctl start songsketch-pi
```

Use the desired start date. If the **BirdNET database itself is erased/replaced and its record IDs restart**, assign a new `source_instance_id` UUID in the private configuration before reconnecting. Keep that ID unchanged across normal relay updates, reboots and restores of the same source database. Deleting the outbox or changing IDs is not a routine repair.

## Real listening health

The relay independently reads these source-verified release 20261014 endpoints:

- `/api/v2/health/audio`: an audio source must report `HEALTHY` and a recent `last_dispatch` timestamp.
- `/api/v2/system/inference`: the configured model must have an attached source, report successful recent windows through `health.state` and `health.lastSuccessAtUnix`, and not be paused. A loaded but failing model, missing model or source marked `notRunning` is a fault.

These evaluate ongoing audio/analysis, so a quiet garden can still be healthy. An HTTP200, `/health` response or recent bird detection alone is not substituted for these checks. Absent, stale, inaccessible or unfamiliar health data produces `unknown`. The default model ID is `BirdNET_V2.4`; set `audio_source_id` for installations with multiple microphones if only one should determine Songsketch health. Otherwise all returned audio sources must be healthy.

Heartbeats are sent every 15 seconds with current health and are **not buffered**: replaying an old healthy heartbeat would give a false live state. Detections and reports are buffered independently.

If BirdNET authentication is enabled, configure `birdnet_token_file` in the relay configuration using a valid credential supported by that BirdNET deployment; the file must be owner-only and readable by `songsketch-pi`. Do not disable an existing security configuration to make a health check green. The bundled local-only container uses BirdNET's first-boot setup and requires API access to be verified there.

## Debugging and automatic maintenance

On the Pi:

```sh
sudo systemctl status songsketch-pi
sudo -u songsketch-pi python3 /opt/songsketch-pi/relay.py --check
sudo -u songsketch-pi python3 /opt/songsketch-pi/relay.py --diagnostics
```

`--check` reads BirdNET contracts without delivering test or real detections. `--diagnostics` prints a safe local summary, including queue depth and faults, without credentials or raw recordings. It does not replace the running process's live health check. The relay HTTP service listens on `127.0.0.1:8081` by default: `/health` is minimal, while `/diagnostics` and `/reports` require the station bearer token. Use SSH or the tunnel, not router port forwarding. To download the reports without putting a token in shell arguments, run this on the Pi:

```sh
sudo -u songsketch-pi python3 - <<'PY'
import json, urllib.request
from pathlib import Path
token = Path('/etc/songsketch-pi/station.token').read_text().strip()
request = urllib.request.Request('http://127.0.0.1:8081/reports', headers={'Authorization': 'Bearer ' + token})
with urllib.request.urlopen(request, timeout=10) as response:
    print(json.dumps(json.load(response), indent=2))
PY
```

Reports are saved locally before upload, grouped by component, repeated at most hourly while the same fault continues, and accompanied by a recovery report when evidence returns. Unsent reports are never pruned; the latest 500 delivered report records are retained. Reports use allow-listed fields/error categories rather than copying arbitrary HTTP responses or environment variables. No raw audio is uploaded by the relay. BirdNET may keep clips locally according to its own settings.

The relay keeps three 2 MB rotated logs and three daily consistent SQLite backups. Docker logs have three 10 MB files. Systemd restarts relay crashes after 15 seconds, bounded to five starts per five minutes; exhausted retries require investigation. Docker restarts a crashed BirdNET container; BirdNET's own audio liveness watchdog attempts source recovery. These mechanisms do not claim to fix unplugged hardware, a full SD card, bad credentials or an unpowered server. An unhealthy-but-running container is not automatically destroyed/recreated by this installer.

## Verified versus still to verify

The automated `tests/test_pi.py` checks paginated history, interrupted scans, persisted outboxes and reports, lost acknowledgements, duplicate suppression, bounded fault reporting, real-health semantics, safe diagnostics and consistent backups. These run without private services or hardware. Shell syntax and unsupported-host checks are validated separately.

Before handing over the physical kit, record: supported OS check; pinned container digest; selected microphone and model; capture/inference health; one genuine species detection; server-offline buffering; relay restart while offline; recovery without duplicate counts; service startup after Pi and server reboots; and restored backup behavior. Actual display performance and longer outdoor operation need their own checks.

## Primary contract references

- [BirdNET-Go 20261014 release](https://github.com/tphakala/birdnet-go/releases/tag/20261014).
- [Pinned detection response and pagination](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/detections/detections.go).
- [Pinned audio health endpoint](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/audio/audio_health.go) and [liveness snapshot](https://github.com/tphakala/birdnet-go/blob/20261014/internal/audiocore/liveness.go).
- [Pinned inference health response](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/system/inference_status.go).
- [Official container paths/device configuration](https://github.com/tphakala/birdnet-go/blob/20261014/Docker/docker-compose.yml) and [release tag publishing](https://github.com/tphakala/birdnet-go/blob/20261014/.github/workflows/docker-build-push.yml).

These are contracts reviewed from source, not evidence that the friend's hardware was tested.

# Garden Pi setup and verification

The Pi runs BirdNET-Go for recognition and the Songsketch relay for delivery, health and reports. Recognition and ordinary painting playback need no AI API key. This implementation is tested against mocked BirdNET APIs and server failures; installation, audio capture and reboot recovery still require the actual Pi and microphone. Do not describe those physical checks as passed.

## The AI-led setup route

Give a local terminal-capable assistant the [setup handoff](ai-setup.md). It runs the existing bootstrap, opens the control panel and uses `scripts/setup-assistant.py` to probe, confirm host identity and commission the Pi. The human supplies the connected hardware, missing site details, a local credential when needed, and the actual host-identity/OS permissions. The following is a reference for the assistant, not a list of terminal chores for the garden keeper.

The Pi must first have power, a usable account, network access and SSH. Reuse supported **64-bit Raspberry Pi OS Bookworm (Debian 12) or Trixie (Debian 13)**. The installer checks an `aarch64` kernel, `arm64` userspace, OS release and Raspberry Pi hardware marker. A preloaded OS does not mean BirdNET is installed. If the card or initial headless access needs Raspberry Pi Imager, identify the exact card and obtain explicit approval before erasing it. The Songsketch helpers do not flash storage.

The local manager pins the explicitly confirmed SSH key, reuses an existing key/agent or accepts a short-lived password locally, and transfers the bundled helper plus private provisioning data. The remote entrypoint is `scripts/commission-pi.py --provision -`, run through `sudo -n`; the manager sends JSON on protected stdin rather than putting a token in arguments. It needs the actual server LAN URL, station identity/token, exact garden latitude/longitude, timezone and any selected microphone ID. The human should not construct this file. The Pi's `localhost` is the Pi, not the Mac.

For a supported installation owned by Songsketch, the helper checks platform, free space and clock; installs the pinned rootful Docker/container and relay; obtains the actual capture inputs; applies the limited configuration below; verifies it; then starts delivery. It selects a microphone automatically only when one sensible capture input is unambiguous. Otherwise it returns `needs_input` with the available choices. A returned `stableId` is preferred to a legacy card-number ID.

A successful commissioning result requires **fresh capture, advancing BirdNET v2.4 inference, readable stored history, a server-acknowledged heartbeat and a healthy relay history scan**. The guide distinguishes that result from a read-only diagnostic run. It still does not prove audio quality, a genuine bird, reboot recovery or outdoor reliability. Those are the human/equipment checks below.

Existing authentication, an unowned container, extra sources/models or unfamiliar storage/settings are preserved and may require review. The helper does not disable authentication to finish setup. In particular, an authenticated BirdNET installation returns `needs_input` with `review_birdnet_access`; unattended credential renewal is not automated by this release. The manager API can deliberately select `use_existing_birdnet`, but the current simple CLI/form does not expose that advanced switch. Inspect the existing installation and use the documented guarded API rather than pretending a new-install command has adopted it.

Setup state is saved locally on the server under `commissioning/state.json`, and on the Pi under `/var/lib/songsketch-pi/commission-status.json`. Read local context with `python3 scripts/setup-assistant.py diagnose`; use `diagnose-pi` with the current job ID for remote read-only checks. A stopped connection may leave an already-started Pi operation running. Diagnose before retrying; cancellation is not rollback. See the [exact CLI contract](ai-setup.md#interfaces-for-the-assistant).

### Manual fallback for an existing release

If a local assistant is unavailable, **Start Songsketch.command** and **Pair Garden Pi.command** remain supported. The latter runs `scripts/pair-pi.sh`, transfers the private station configuration over SSH, and installs via sudo after confirmation. This older path leaves BirdNET's microphone/location wizard to the operator; it does not perform the new commissioning checks automatically.

Its optional SSH tunnel opens BirdNET at **http://localhost:18080** and the relay's minimal health endpoint at **http://localhost:18081/health**. Keep the tunnel open while using those pages. `/health` proves only that the relay's HTTP process answers, not that it can hear. Use the configuration reference below to finish BirdNET. Neither delivery nor ongoing recognition depends on leaving that browser tunnel open.

`bash scripts/pair-pi.sh --check` inventories the connection/devices without installing. On the Pi, `sudo bash scripts/install-pi.sh --check` checks the platform without changes. `sudo bash scripts/install-pi.sh --skip-birdnet` installs the relay while retaining an existing BirdNET installation; version and authorised API access still need separate checks.

## BirdNET readiness checklist

Complete these checks before relying on live bird counts. **“Software installed”, a visible web page, and an audio device listed by Linux are three different checks; none alone proves recognition works.** Keep a record of the exact microphone and USB adapter models, selected capture device, BirdNET release/model, coordinates, time, and the date these checks passed.

### Before installation: the physical kit and Pi

- [ ] **Suitable computer and storage.** Use the Pi 5 kit for this MVP. BirdNET's pinned hardware guide describes 2 GB RAM as sufficient for one BirdNET v2.4 source; additional models need more resources. It recommends a 64 GB or larger endurance microSD card and excludes Pi 3/Zero. Reuse an appropriate supplied card rather than reflashing unnecessarily. Keep free space for the container image, database and clips. [BirdNET hardware guidance](https://github.com/tphakala/birdnet-go/blob/20261014/doc/wiki/hardware.md).
- [ ] **Power and cooling.** Use the Pi 5's suitable 5 V/5 A supply, preferably the official 27 W unit, and a fitted cooler with airflow. A 3 A supply limits USB peripheral power to 600 mA; the fan and USB devices share a power budget. Keep the microphone away from fan noise. [Raspberry Pi power requirements](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply), [Active Cooler](https://www.raspberrypi.com/products/active-cooler/).
- [ ] **Correct microphone input and power.** For the **3.5 mm Clippy EM272**, the USB sound card must have a compatible microphone input providing **plug-in power**. A headphone-only dongle or unpowered line input cannot substitute. The mono Clippy's TRS plug carries the same mono signal on both channels; it is not a two-capsule stereo microphone. XLR Clippys are different assemblies requiring phantom power. Do not connect a 3.5 mm mic or bare capsule directly to 48 V phantom power, or assume a passive plug adapter converts the power correctly. Confirm the exact adapter's specification and test the actual pair. [Micbooster's connector/power distinctions](https://micbooster.com/product/clippy-em272-microphone/), [Primo capsule datasheet](https://primomic.com/pdf/EM272.pdf).
- [ ] **Placement.** Use a windshield, protect the installation from rain, and keep the microphone clear of wind, rubbing cables, the enclosure wall and cooling airflow. A windshield is not evidence of waterproofing. The manufacturer's manual recommends shelter from wind; outdoor weather protection still needs a physical review. [Clippy manual](https://micbooster.com/manuals/Clippy%20Stereo%20FC042%20%26%20FC049%20Manual.pdf).
- [ ] **OS, account and network.** The Songsketch installer supports Raspberry Pi OS/Debian 12 or 13 with 64-bit ARM userspace. Check `uname -m` gives `aarch64` **and** `dpkg --print-architecture` gives `arm64`. Have the SSH username/password or key, enabled SSH, and a working home-network connection. Ethernet is a simple first-test route; garden Wi-Fi must be tested where the kit will sit. Avoid guest-network isolation between Pi and server. First installation needs internet for OS packages and the container image. [Official headless setup](https://www.raspberrypi.com/documentation/computers/configuration.html#headless-setup).
- [ ] **Correct clock.** On the Pi, `timedatectl status` should show the correct date/time and a synchronized clock; use Europe/London for local time. Also check the Mac/server clock. The image's timezone setting does not set the underlying system clock. Incorrect time affects detection timestamps, monthly counts and seasonal species filtering. [Raspberry Pi time configuration](https://www.raspberrypi.com/documentation/computers/configuration.html), [BirdNET geographic/seasonal filtering](https://github.com/tphakala/birdnet-go/blob/20261014/doc/wiki/detection-pipeline.md#range-filter).

For a read-only first inventory on the Pi:

```sh
uname -m
dpkg --print-architecture
free -h
df -h /
timedatectl status
cat /proc/asound/cards
```

The headless commissioner checks platform, at least 2 GB of free installation space and clock synchronization; it does not certify RAM headroom, cooling, plug-in power or audio quality. The lower-level installer alone does not perform all commissioning checks. `/dev/snd` can exist because of HDMI sound even when no microphone is connected. The actual capture input must appear in BirdNET's device list.

For the selected UGREEN 30724 and Clippy, follow the [exact connector, interference and physical audio checks](birdnet-pi-reliability.md#ugreen-30724-and-clippy-compatibility-and-noise). The assistant runs software checks; the installer supplies a short test sound and confirms that playback is clean. Capture/inference health alone does not establish analog microphone quality.

### The configuration the helper applies

The [bundled commissioner](../scripts/commission-pi.py) applies these settings only to its supported, owned BirdNET installation, backs up the existing configuration and reads settings back to verify them. With unmanaged or complex installations it reports what needs review instead of rewriting them. These are also the reference choices for the manual fallback.

1. **One actual garden input.** Use BirdNET's returned capture list. Prefer its stable device identifier; do not guess `hw:0,0` or select HDMI/default/loopback blindly. Ambiguous inputs need a selection. A stable identifier reduces dependence on card numbering, but the real USB arrangement still needs a restart test. See the capture-selection rules in [the commissioner](../scripts/commission-pi.py).
2. **Exact garden location and UK labels.** Configure the property's actual latitude/longitude and `en-uk` labels. “Dorset” alone is insufficient, and 0,0 is rejected. The helper sets the Pi timezone from the server setting and checks synchronized time; Europe/London is the default. An existing container with a different timezone needs review rather than destructive recreation.
3. **Threshold 0.7 and built-in BirdNET v2.4.** The helper enables the `birdnet` model, associates it with the selected 48 kHz input and checks advancing inference. It does not install separate Python/TensorFlow models or request an AI API key. Songsketch still applies its own qualifying threshold; lower records can be retained without entering counts or triggering paintings. [Pinned model/default settings](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml), [container contents](https://github.com/tphakala/birdnet-go/blob/20261014/Dockerfile).
4. **Day and night coverage, including owls.** The commissioning plan disables quiet hours and the daylight filter for the single-source MVP. This avoids suppressing daytime owl detections under the pinned default filter; it is not a guarantee that every owl call will be recognised. Review false positives during the trial. [Pinned filtering defaults](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml).
5. **Stored history on; new audio clips off.** SQLite output stays enabled for the relay. The commissioning plan disables clip export to limit routine storage of audio; it does not delete existing recordings. Listening to the live input during commissioning still matters. Do not confuse clip retention with detection-history retention.
6. **Actual audio quality remains a listening check.** Listen through BirdNET's live audio/spectrogram and check for useful garden sound, clipping, hiss, fan noise or an unplugged input. A fresh source starts at default gain; existing single-source gain is preserved. Adjust only from observed sound. A loaded model or an available audio device is not proof of successful capture/inference. [Pinned audio pipeline](https://github.com/tphakala/birdnet-go/blob/20261014/doc/wiki/detection-pipeline.md).
7. **Optional integrations stay optional.** BirdWeather uploads, MQTT, weather providers and paid AI tools are unnecessary for this path. No public internet exposure is configured.

### Storage, access and startup checks

- [ ] **SQLite recording stays enabled.** Songsketch imports BirdNET's stored records, so disabling database output breaks this route even if audio analysis continues. In the bundled container the working directory is `/data`, and the default SQLite path `birdnet.db` is on the persistent data mount. Keep `/config` and `/data` writable and retained across container restarts. [Pinned database settings](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml), [container working directory](https://github.com/tphakala/birdnet-go/blob/20261014/Dockerfile).
- [ ] **Audio clip policy is intentional.** BirdNET itself enables clip export by default, but the AI commissioning plan disables it for this MVP without deleting existing clips. The manual fallback must make that choice explicitly. If clip recording is enabled later, set and verify a deliberate retention policy; usage cleanup is not a promise of unlimited storage. Clip cleanup and detection-history retention are separate. Keep enough detection history for monthly counts and the longest expected relay outage; do not delete the database as a routine disk cleanup. [Pinned clip-retention settings](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml).
- [ ] **There is operating headroom.** BirdNET's pinned entrypoint refuses startup with less than **1,024 MB free in `/data`**. Check free disk after installation and during the trial, rather than waiting for the relay's much lower emergency pause threshold. The entrypoint sets device permissions for our ordinary rootful Docker route before running as its application user. Rootless Docker/Podman is a different deployment and needs separate device-permission validation. [Pinned startup checks and permissions](https://github.com/tphakala/birdnet-go/blob/20261014/Docker/entrypoint.sh).
- [ ] **The relay can read every required API.** Run `sudo -u songsketch-pi python3 /opt/songsketch-pi/relay.py --check`. Confirm detections, audio health and inference status are readable; a dashboard login in your browser does not authenticate the relay. For existing protected BirdNET installations, read the authentication limitation below before handover.
- [ ] **Prove the whole path.** Verify live garden audio, advancing inference, a genuine stored species detection in BirdNET, and the same species/time in Songsketch. An unknown species can appear in history without a painting. Songsketch's simulation button proves playback only. No bird calls during a quiet period does not prove failure.
- [ ] **Reboot and outage tests pass.** After setup, reboot the Pi deliberately and confirm the selected capture device, model and relay recover. Test a temporary server outage and subsequent replay without duplicate counts. New commissioning prefers the returned stable device ID. Older configurations can still use numeric IDs, and changing USB connections can change device identity. Recheck the actual source if health fails, and keep a consistent USB arrangement.

The relay's three local backups protect **its own queue and reports**, not the complete BirdNET installation. Preserve BirdNET's configuration and a consistent database backup separately if recovery of its source history is required. A mounted data directory survives container replacement but not a failed SD card. Store an off-device recovery copy before unattended handover; do not copy a live SQLite database file in isolation from its write-ahead log.

Close the SSH tunnel only after setup checks pass. It is needed for the Mac to view BirdNET, not for Pi-to-Songsketch delivery or ongoing recognition. For a fresh local-only installation, the BirdNET web port remains bound to Pi loopback; opening a router port is not part of this setup.

## What the installer changes

| Location | Purpose |
|---|---|
| `/opt/songsketch-pi/relay.py` | Release-managed relay code; replaced on a repeat install |
| `/etc/songsketch-pi/config.json` | Station/server settings and persistent BirdNET database identity |
| `/etc/songsketch-pi/station.token` | Owner-only station credential |
| `/etc/songsketch-pi/birdnet-image.lock` | Resolved immutable container digest from release 20261014 |
| `/var/lib/songsketch-pi/` | Durable SQLite outbox, scan checkpoint, reports, rolling logs and three daily backups |
| `/var/lib/songsketch-pi/commission-status.json` | Private saved commissioning evidence and next action |
| `/var/lib/songsketch-pi/commission-backups/` | Up to three private BirdNET configuration backups made before owned-setting changes |
| `/var/lib/songsketch-birdnet/` | BirdNET settings, recognition database, additional downloaded models and any locally configured audio clips; stock models are inside the pinned image |
| `songsketch-pi.service` | Unprivileged relay startup and bounded crash restarts |
| `songsketch-birdnet` | Managed Docker container with restart policy and bounded Docker logs |

The lower-level installer preserves history and existing configuration; the commissioner deliberately updates only the owned, supported settings described above after taking a configuration backup. If Docker is missing it installs the OS `docker.io` package; it does not run a downloaded shell bootstrap. It pulls `ghcr.io/tphakala/birdnet-go:20261014`, records the registry content digest and runs that immutable digest. Repeat installation uses the lock and leaves an existing managed container intact; it does not silently upgrade BirdNET. Do not edit the image lock as an update strategy. Actual first-time image download and Pi execution remain hardware verification steps.

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

These evaluate ongoing audio/analysis, so a quiet garden can still be healthy. An HTTP200, `/health` response or recent bird detection alone is not substituted for these checks. Absent, stale, inaccessible or unfamiliar health data produces `unknown`. The default model ID is `BirdNET_V2.4`. The supported commissioning route selects one physical microphone; all returned audio sources must be healthy. Do not set the optional `audio_source_id` to select a microphone on this release: BirdNET uses different identifiers for audio health and model attachments, and that advanced mapping is not yet supported. An existing multi-source installation needs separate review.

Heartbeats are sent every 15 seconds with current health and are **not buffered**: replaying an old healthy heartbeat would give a false live state. Detections and reports are buffered independently.

**Authentication boundary:** the fresh bundled container uses BirdNET's default authentication settings and exposes its web port only on Pi loopback. This is the simple MVP route; the SSH account controls remote access to its setup UI. The Songsketch station token is a separate credential and cannot authenticate to BirdNET.

If BirdNET authentication is already enabled, both health endpoints require authorized access. The relay can read a bearer credential from `birdnet_token_file` (owner-only, readable by `songsketch-pi`), but it does **not** log in, refresh tokens or renew an expired session. BirdNET's pinned default access-token lifetime is **one hour**. Therefore copying a browser access token into a file is not an unattended setup. Existing authenticated deployments need an operator-designed, narrowly scoped access/renewal arrangement and an expiry/restart test; this release does not automate that configuration. Do not disable an existing security configuration just to make a health check green. [Audio route protection](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/audio/audio_health.go), [inference route protection](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/system/handler.go), [token validation and expiry](https://github.com/tphakala/birdnet-go/blob/20261014/internal/security/oauth.go), [default lifetime](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml).

## Debugging and automatic maintenance

The local assistant first reads the setup checkpoint and diagnostic packet, then makes at most two evidence-based repair cycles before reporting the specific remaining blocker. Fixed remote diagnosis is available through `setup-assistant.py diagnose-pi`; it does not alter installed settings or restart services. Returned diagnostics are not a commissioning pass.

For deeper inspection, the assistant can use these fixed read-only checks on the Pi:

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

The automated `tests/test_pi.py` covers relay/history behavior. `tests/test_commission_pi.py`, `tests/test_commissioning.py` and `tests/test_setup_integration.py` exercise the commissioning, guarded transport and local setup integration using isolated or simulated dependencies. The current pass record belongs in [verification.md](verification.md). These checks do not execute a real microphone or commission the garden Pi; source review and a mocked success are not hardware evidence.

Before handing over the physical kit, record: supported OS check; pinned container digest; selected microphone and model; capture/inference health; one genuine species detection; server-offline buffering; relay restart while offline; recovery without duplicate counts; service startup after Pi and server reboots; and restored backup behavior. Actual display performance and longer outdoor operation need their own checks.

## Primary contract references

- [BirdNET-Go 20261014 release](https://github.com/tphakala/birdnet-go/releases/tag/20261014).
- [Pinned detection response and pagination](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/detections/detections.go).
- [Pinned audio health endpoint](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/audio/audio_health.go) and [liveness snapshot](https://github.com/tphakala/birdnet-go/blob/20261014/internal/audiocore/liveness.go).
- [Pinned inference health response](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/system/inference_status.go).
- [Official container paths/device configuration](https://github.com/tphakala/birdnet-go/blob/20261014/Docker/docker-compose.yml) and [release tag publishing](https://github.com/tphakala/birdnet-go/blob/20261014/.github/workflows/docker-build-push.yml).

These are contracts reviewed from source, not evidence that the friend's hardware was tested.

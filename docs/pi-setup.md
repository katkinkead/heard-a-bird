# Garden Pi setup and verification

The Pi runs BirdNET-Go for recognition and the Songsketch relay for delivery, health and reports. Recognition and ordinary painting playback need no AI API key. This implementation is tested against mocked BirdNET APIs and server failures; installation, audio capture and reboot recovery still require the actual Pi and microphone. Do not describe those physical checks as passed.

## The short setup route

1. Check the supplied SD card. Reuse supported **64-bit Raspberry Pi OS Bookworm (Debian 12) or Trixie (Debian 13)**. The installer checks an `aarch64` kernel, `arm64` userspace, the OS release and the Raspberry Pi hardware marker. It does not flash or erase the card. First-boot account, Wi-Fi/Ethernet and SSH setup are human steps.
2. Connect the microphone through its compatible USB audio input. A 3.5 mm Clippy needs plug-in power from the microphone input; see the readiness checklist below. Start Songsketch on the MacBook first. Keep it awake, with its firewall allowing the Songsketch server on the trusted home network.
3. Open **Pair Garden Pi.command**, or run `bash scripts/pair-pi.sh` from this release. Enter the Pi SSH account/address and the server's LAN URL. A Pi must use the Mac's LAN address, for example `http://192.168.1.20:8765`, never `localhost`. Compare the SSH host-key fingerprint before accepting a new host. The helper does not disable host verification.
4. The helper transfers this release's relay and installer over SSH, together with the station token already created by the local server. The token is not printed or placed in command arguments. Confirm the intended Pi; the installer uses `sudo` on it. Software download needs internet on first installation.
5. Accept the setup tunnel. BirdNET opens at **http://localhost:18080** on the Mac. Complete its wizard: select the actual USB audio input, set the garden's location, and choose **Balanced (0.7)**. The installer sets the container timezone to Europe/London; verify the Pi's date and clock separately. Keep **BirdNET v2.4** enabled for this tested species contract. Do not guess a microphone device name. The container's UI is bound to Pi loopback; keep the SSH tunnel open during setup.
6. Check Songsketch's dashboard. A connected Pi with **listening unknown** means the health evidence has not yet established successful capture and recognition; it is not a healthy-listening result. Verify a real recorded detection and the correct artwork after the clearly labelled simulation test.

The helper also tunnels the Pi's minimal health endpoint to **http://localhost:18081/health**. A successful result proves only that the relay's local HTTP process answers. It deliberately does not certify audio or inference.

`bash scripts/pair-pi.sh --check` performs a connection/device inventory without installing. On the Pi, `sudo bash scripts/install-pi.sh --check` checks the supported platform without changes. `sudo bash scripts/install-pi.sh --skip-birdnet` installs the relay while retaining an existing BirdNET installation; verify that installation's version and API access separately.

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

The current installer does not certify RAM, cooling, plug-in power, capture quality or clock synchronization. `/dev/snd` can exist because of HDMI sound even when no microphone is connected. The actual capture input must appear in BirdNET's device list.

### In BirdNET: finish setup, then prove capture and analysis

1. **Choose the garden input.** In the wizard's audio-source step select the USB sound card/microphone from the actual detected list, rather than HDMI or an assumed `hw:0,0`. Keep one source for the MVP. Save the selection. The wizard obtains this list from the device API and persists the selected sound card. [Pinned audio wizard](https://github.com/tphakala/birdnet-go/blob/20261014/frontend/src/lib/desktop/features/wizard/steps/AudioSourceStep.svelte).
2. **Choose the property location and UK labels.** Use the location map/search for the garden, check its coordinates, and select English (UK) species labels. “Dorset” is a region, not an exact location: do not copy another station's coordinates or leave 0,0. The wizard saves latitude, longitude and label language; timezone is handled separately. [Pinned location wizard](https://github.com/tphakala/birdnet-go/blob/20261014/frontend/src/lib/desktop/features/wizard/steps/LocationLanguageStep.svelte).
3. **Choose Balanced (0.7).** This is the pinned wizard's recommended preset and matches Songsketch's default qualifying threshold. BirdNET may subsequently save lower-confidence records through its dynamic threshold; Songsketch stores them but excludes scores below its own threshold from counts and painting triggers. Raising BirdNET to 0.9 means it will never send Songsketch the discarded 0.7–0.9 results. [Pinned detection wizard](https://github.com/tphakala/birdnet-go/blob/20261014/frontend/src/lib/desktop/features/wizard/steps/DetectionStep.svelte).
4. **Confirm the model is running.** Keep built-in **BirdNET v2.4** enabled and associated with this source. In **System → AI Models & Inference**, look for that model, an attached source and advancing successful inference. An empty enabled-model list is a valid BirdNET configuration, but cannot identify birds. The pinned ARM64 container includes stock ONNX models and runtime libraries; the standard installation does not require separately installing TensorFlow/Python models or buying a BirdNET API key. Additional gallery models and custom model paths are outside this tested MVP. [Pinned model defaults](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml), [container contents](https://github.com/tphakala/birdnet-go/blob/20261014/Dockerfile).
5. **Listen before adjusting gain.** Use BirdNET's live audio/spectrogram to confirm the selected input contains real garden sound. Start with default input gain, then adjust only enough to capture usable sound without clipping or a dominating hiss. There is no universal correct gain number for every USB interface. BirdNET v2.4 analyses mono, 48 kHz, three-second windows; the audio pipeline handles supported resampling. Start with ordinary bird capture and default overlap rather than adding EQ, multiple models or ultrasonic settings. Output/playback loudness is not proof that the inference input has improved. [Pinned audio pipeline](https://github.com/tphakala/birdnet-go/blob/20261014/doc/wiki/detection-pipeline.md).
6. **Review night and owl settings.** Keep quiet hours off if the garden should listen overnight. The pinned default also enables a daylight filter covering `Strigiformes` (owls), which can suppress genuine daytime owl detections. For this project's all-day owl coverage, deliberately disable that daylight filter or narrow its species list, then assess false positives. This is a coverage choice, not proof that every owl call will be identified. [Pinned quiet-hours/daylight settings](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml).
7. **Leave optional integrations optional.** BirdWeather uploads, MQTT, weather providers, public internet exposure and paid OpenAI features are not required to recognize local bird audio or deliver it to Songsketch. The relay uses the stored-detections API. Finish the wizard and confirm settings persist after a page reload.

### Storage, access and startup checks

- [ ] **SQLite recording stays enabled.** Songsketch imports BirdNET's stored records, so disabling database output breaks this route even if audio analysis continues. In the bundled container the working directory is `/data`, and the default SQLite path `birdnet.db` is on the persistent data mount. Keep `/config` and `/data` writable and retained across container restarts. [Pinned database settings](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml), [container working directory](https://github.com/tphakala/birdnet-go/blob/20261014/Dockerfile).
- [ ] **Audio clip policy is intentional.** BirdNET enables clip export by default. Its default usage cleanup starts at 80% disk usage and retains a minimum number of clips per species; this is not a promise of unlimited storage. For the MVP, either disable clip saving after audio verification or set a deliberate retention policy. Clip cleanup and detection-history retention are separate. Keep enough detection history for monthly counts and the longest expected relay outage; do not delete the database as a routine disk cleanup. [Pinned clip-retention settings](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml).
- [ ] **There is operating headroom.** BirdNET's pinned entrypoint refuses startup with less than **1,024 MB free in `/data`**. Check free disk after installation and during the trial, rather than waiting for the relay's much lower emergency pause threshold. The entrypoint sets device permissions for our ordinary rootful Docker route before running as its application user. Rootless Docker/Podman is a different deployment and needs separate device-permission validation. [Pinned startup checks and permissions](https://github.com/tphakala/birdnet-go/blob/20261014/Docker/entrypoint.sh).
- [ ] **The relay can read every required API.** Run `sudo -u songsketch-pi python3 /opt/songsketch-pi/relay.py --check`. Confirm detections, audio health and inference status are readable; a dashboard login in your browser does not authenticate the relay. For existing protected BirdNET installations, read the authentication limitation below before handover.
- [ ] **Prove the whole path.** Verify live garden audio, advancing inference, a genuine stored species detection in BirdNET, and the same species/time in Songsketch. An unknown species can appear in history without a painting. Songsketch's simulation button proves playback only. No bird calls during a quiet period does not prove failure.
- [ ] **Reboot and outage tests pass.** After setup, reboot the Pi deliberately and confirm the selected capture device, model and relay recover. Test a temporary server outage and subsequent replay without duplicate counts. Device enumeration can change after USB changes/reboots, so recheck the capture choice if health fails; do not assume the old card number is stable. Keep a consistent USB arrangement. [BirdNET maintainer's current microphone/reboot guidance](https://github.com/tphakala/birdnet-go/wiki/FAQ#my-usb-sound-card-stops-working-after-a-reboot-i-have-to-reselect-it-every-time).

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
| `/var/lib/songsketch-birdnet/` | BirdNET settings, recognition database, additional downloaded models and any locally configured audio clips; stock models are inside the pinned image |
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

**Authentication boundary:** the fresh bundled container uses BirdNET's default authentication settings and exposes its web port only on Pi loopback. This is the simple MVP route; the SSH account controls remote access to its setup UI. The Songsketch station token is a separate credential and cannot authenticate to BirdNET.

If BirdNET authentication is already enabled, both health endpoints require authorized access. The relay can read a bearer credential from `birdnet_token_file` (owner-only, readable by `songsketch-pi`), but it does **not** log in, refresh tokens or renew an expired session. BirdNET's pinned default access-token lifetime is **one hour**. Therefore copying a browser access token into a file is not an unattended setup. Existing authenticated deployments need an operator-designed, narrowly scoped access/renewal arrangement and an expiry/restart test; this release does not automate that configuration. Do not disable an existing security configuration just to make a health check green. [Audio route protection](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/audio/audio_health.go), [inference route protection](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/system/handler.go), [token validation and expiry](https://github.com/tphakala/birdnet-go/blob/20261014/internal/security/oauth.go), [default lifetime](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml).

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

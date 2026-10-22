# Real BirdNET validation

On 22 October 2026 we ran the actual ARM64 BirdNET-Go `20261014` container and its BirdNET v2.4 model, fed it an upstream Tawny Owl recording through RTSP, and delivered its stored detections through the production relay into a disposable Songsketch server. This is developer QA, not another installation step.

## What passed

| Check | Observed result |
| --- | --- |
| Real configuration API | No-key bootstrap, cookie/CSRF session and all five source-independent settings sections accepted PATCH and matched readback |
| Saved configuration | BirdNET restarted; read-only checks confirmed location/filter, model, owl/daylight settings, database output, quiet hours and audio export settings persisted |
| Model and audio | Stock ARM64 ONNX INT8 BirdNET v2.4; 48 kHz mono audio; the production commissioning check observed fresh audio and advancing successful inference |
| Real recognition | Repeated 15-second upstream owl clip produced ten stored `Strix aluco` records. Stored confidence was 1.0; this is a classifier score, not a guarantee of accuracy |
| Delivery | Production `Relay.poll` and `Relay.deliver` sent all ten records over real local HTTP into Songsketch SQLite; exact identities/values and qualifying counts matched |
| Replay | A second poll left ten records and an empty relay outbox |
| Missing artwork | An intentionally empty, isolated catalogue queued one missing-art notice with zero send attempts; no SMTP or external email was used |
| Stream stopped | Stored-history delivery still passed; later inference/listening observations became unknown rather than being fabricated as healthy |

Ten records came from repeated playback of one recording. They do not represent ten individual owls, a species-accuracy benchmark or ten garden visits. Rendering was not part of this audio/API run.

The lab used a separate Colima ARM64 Linux VM, no home-folder mounts, disposable container storage and loopback-only API ports. It did not emulate Pi firmware or exercise the USB microphone, SSH installer, physical power supply, network range or full service installation. The production Pi hardware guards were left intact.

## Bugs and safeguards

- Real BirdNET emits RFC3339 timestamps with up to nine fractional digits. Python 3.9 rejected the observed eight-digit audio timestamp, so healthy capture appeared unknown. The relay now safely converts fractions to microsecond precision; regression tests use the actual observed format and cover offsets, stale/future values and malformed input.
- Commissioning now checks the exact tested release and rechecks settings after either a requested restart or a recovery restart. Settings lost across restart stop setup before the relay is marked ready.
- Fresh managed-copy verification caught an omitted Practice Garden launcher. The launcher is now included; the test checks the copied application's own preflight.
- Optional per-source health filtering is not supported for multi-input stations: BirdNET audio watchdog IDs differ from inference attachment names. The supported one-microphone commissioning path is unaffected. The documentation no longer recommends that optional setting.

## Repeating the API and delivery checks

These scripts are developer tools. Keep their Docker, VM, audio and test-server dependencies out of the illustrated setup journey. First start a **disposable** instance of the pinned BirdNET image, with its API published on `127.0.0.1:18080`. Never point the settings check at an existing station. The scripts reject external hosts, credential-bearing URLs and the production port 8080.

```sh
# Apply the production planner's source-independent settings to the lab.
python3 scripts/qa-birdnet-api.py --url http://127.0.0.1:18080 \
  --allow-lab-settings --report /tmp/birdnet-api-before.json

# Restart only your lab container, then verify without writing settings.
python3 scripts/qa-birdnet-api.py --url http://127.0.0.1:18080 \
  --report /tmp/birdnet-api-after.json

# Stop the audio publisher and let pending detections settle first.
python3 scripts/qa-birdnet-delivery.py --url http://127.0.0.1:18080 \
  --expected-species 'Strix aluco' --report /tmp/birdnet-delivery.json
```

The API check derives the common settings from `settings_plan`; it never submits a made-up physical capture device or replaces RTSP sources. It uses synthetic Dorset coordinates (`50.72, -2.44`) and `Europe/London` for the lab, not a private garden address. Read-only mode fails on configuration drift. Detection queries explicitly select the station's current local day; an unscoped endpoint returned an empty result during the original run even when the dated query returned stored detections.

The delivery check creates its own temporary server, database, credentials, empty art catalogue and relay outbox. Background maintenance, SMTP and AI workers are off. It requires an actual qualifying stored detection of the named species, compares complete normalized records, and fails if the upstream history changes during the check. Current audio health is a separate observation: stopped audio must not turn successful history delivery into a claim that live listening works. Reports are written with mode `0600` and omit raw settings, credentials and response bodies.

### Audio setup used in this run

The [pinned default configuration](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.yaml) was copied into the disposable container's `/config/config.yaml`. Its physical `realtime.audio.sources` list was replaced with `[]`; one enabled `realtime.rtsp.streams` entry used name `QA owl stream`, URL `rtsp://qa-rtsp:8554/owl`, type `rtsp`, transport `tcp`, models `[birdnet]` and quiet hours disabled. Both BirdNET and MediaMTX shared a private Docker bridge; only the test ports were published on loopback. Disable unrelated weather integrations and thumbnails in the initial lab configuration. Default telemetry and external notification integrations remain off.

MediaMTX `1.16.1` used `MTX_RTSPTRANSPORTS=tcp` and its default path configuration. Do not add a duplicate `all_others` alias; that prevented its first startup. FFmpeg streamed the locally downloaded [upstream test WAV](https://github.com/tphakala/birdnet-go/blob/20261014/tawnyowl.wav) with:

```sh
ffmpeg -re -stream_loop -1 -i /path/to/tawnyowl.wav -t 120 \
  -c:a pcm_s16be -ar 48000 -ac 1 -rtsp_transport tcp \
  -f rtsp rtsp://127.0.0.1:18554/owl
```

Use big-endian PCM for this RTSP path; the initial little-endian attempt did not establish a stream. The actual run repeated playback before and after restart. The recorder's attribution was not established independently of the repository's general licence, so the audio is **not bundled** with Songsketch. Download it only for a deliberate local test and review permissions before redistributing it.

The baseline threshold was 0.7, with upstream adaptive thresholds enabled (trigger 0.9, minimum 0.2, 24-hour validity). Songsketch separately applies its 0.7 counting threshold. Do not equate the BirdNET baseline with a guaranteed minimum for every stored row. The lab ran with daylight filtering and quiet hours disabled so the owl could be analysed during daytime.

## Evidence and limits

Selected, reviewed evidence is retained in [qa-evidence/2026-10-22](qa-evidence/2026-10-22): [runtime and hashes](qa-evidence/2026-10-22/runtime.json), [initial API writes](qa-evidence/2026-10-22/api-first.json), [post-restart readback](qa-evidence/2026-10-22/api-after-restart.json), [delivery](qa-evidence/2026-10-22/delivery.json) and [delivery after stream stop](qa-evidence/2026-10-22/delivery-after-stream-stop.json). These are observations from the stated run, not continuously updated health. The first API report predates the later date-scoped queries and mutation-outcome reporting improvements.

The image was pinned to `ghcr.io/tphakala/birdnet-go@sha256:4dec04b29548de6c27d1559e8ad0e7e20e2727655ef8a712571e6929e329290a`; its reported version was exactly `20261014`. Source, image, model, range-model and audio hashes are recorded separately. The [upstream release](https://github.com/tphakala/birdnet-go/releases/tag/20261014) and [source configuration types](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.go) are the API/configuration references.

This is one successful real-recognition smoke test. The broader [release-validation matrix](release-validation.md) still includes a varied audio corpus, silence/noise, deliberate decoder/model failures, real SMTP, browser fault uploads, restore, clean virtual installation and physical commissioning. It is not marked fully passed by this run.

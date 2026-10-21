# BirdNET and Pi reliability notes

Checked against BirdNET-Go release **20261014** and the primary references below on 21 October 2026. These are failure modes worth checking, not measured failure rates. The installed hardware has not been tested. Start with `python3 scripts/commission-pi.py --diagnose` on the Pi; it is read-only. Use the [AI setup workflow](ai-setup.md) for its guarded SSH transport and bounded recovery.

## Checks that distinguish different failures

| Symptom | Evidence to inspect | Appropriate response |
|---|---|---|
| Installation will not start | Both `uname -m` and `dpkg --print-architecture`; storage free space; image digest | Use 64-bit Raspberry Pi OS userspace (`arm64`), not just a 64-bit kernel. Keep the pinned image; do not move to `latest` to hide a fault. |
| No capture source | Actual ALSA capture node, BirdNET device inventory and selected stable ID | HDMI playback devices do not prove a microphone exists. Plug in the interface; choose the exact returned source if more than one is suitable. Avoid hardcoding card numbers across boots. |
| Capture exists but audio is silent or distorted | Short local listening check, input level and clipping; plug type and interface power | Confirm the microphone/interface pairing and gain before restarting software. A USB interface being detected does not prove the mic is powered. |
| BirdNET page loads, but listening is unhealthy | `/api/v2/health/audio` dispatch freshness and `/api/v2/system/inference` advancing successful inference timestamps | A responding web server and a quiet garden are both insufficient evidence of working inference. Investigate stale capture/model state; only restart services the installer owns. |
| Unexpectedly few species, or no owls | Garden coordinates, date/time, model selection, confidence, daylight and quiet-hours settings | Use the actual location and `Europe/London` timezone for Dorset. Keep the MVP's single BirdNET v2.4 model, 0.7 threshold, daylight filter off and quiet hours off. Do not fabricate detections or lower confidence automatically to make a test pass. |
| Audio device permission denied | Device mapping, container ownership, pinned entrypoint and host audio permissions | The supported installer is rootful Docker with `/dev/snd` access. Rootless Docker/Podman needs a different permission arrangement; don't solve this by disabling API authentication. |
| Stops after accumulating data | Filesystem space, writable `/data`, SQLite integrity and clip settings | Keep local clip export disabled for MVP. Preserve detection history and the relay outbox. The pinned container entrypoint refuses startup below 1024MiB free on `/data`; investigate before the disk reaches that boundary. |
| Detections stop reaching Songsketch | BirdNET history API, auth response, relay queue, last server acknowledgement | Check expired/invalid API credentials and LAN reachability separately. Restore the connection and replay durable queued events with their existing IDs; do not reset the queue or invent new IDs. |
| Pi disappears or USB disconnects | Current/historical undervoltage and throttling flags, temperature, cable and power chain | Use the power diagnostic below. More USB allowance cannot repair a weak supply. Check cooling and power under the real BirdNET workload. |
| New setup works until reboot | Services, stable capture source, clock synchronization, server address and real post-reboot detection | Verify an intentional reboot and a short server outage before leaving the garden unattended. A software unit test does not replace this acceptance check. |

The relay supplies power/thermal telemetry when the Pi exposes it; missing readings mean **unknown**. Temperature alerts are operational thresholds rather than proof of a defective board. Hardware acceptance still requires the actual enclosure, weather, microphone and power chain.

## Primary evidence behind the checks

- [BirdNET hardware guidance, pinned release](https://github.com/tphakala/birdnet-go/blob/20261014/doc/wiki/hardware.md): Pi 5 with 2GB is sufficient for a single-source BirdNET v2.4 installation; 64-bit OS is required. High-endurance storage and 48kHz-capable audio input are recommended. More models/streams demand more resources. Songsketch deliberately uses the smaller single-model setup.
- [Pinned audio-device selection](https://github.com/tphakala/birdnet-go/blob/20261014/frontend/src/lib/utils/audioDevices.ts), [audio health endpoint](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/audio/audio_health.go), [inference endpoint](https://github.com/tphakala/birdnet-go/blob/20261014/internal/api/v2/system/handler.go): use stable device IDs and separate capture/inference evidence. Runtime API compatibility is checked by the commissioning helper.
- [Detection pipeline](https://github.com/tphakala/birdnet-go/blob/20261014/doc/wiki/detection-pipeline.md) and [configuration](https://github.com/tphakala/birdnet-go/blob/20261014/internal/conf/config.go): model processing, location/season filtering, thresholds and schedules affect results. Songsketch's policy is in `scripts/commission-pi.py`; it preserves unsupported existing configurations for review.
- [Container entrypoint](https://github.com/tphakala/birdnet-go/blob/20261014/Docker/entrypoint.sh): data permissions, device permission handling, timezone selection and the startup free-space check. [Dockerfile](https://github.com/tphakala/birdnet-go/blob/20261014/Dockerfile): packaged runtime and models. Keep the retained image digest so these assumptions do not silently change.
- [Clippy manufacturer](https://micbooster.com/product/clippy-em272-microphone/): 3.5mm Clippy variants need plug-in power; XLR versions need phantom power. [Primo EM272 capsule datasheet](https://primomic.com/pdf/EM272.pdf) is a capsule specification, not proof of a USB adapter's compatibility. Confirm the exact microphone and USB interface model; a generic connector description is insufficient.
- [Official Raspberry Pi throttling diagnostics](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled): bits0–3 describe current conditions; bits16–19 record past conditions. Check both before/after a sustained run. [Cooling white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-003608-WP-2-Cooling%20a%20Raspberry%20Pi%20device.pdf): cooling affects sustained performance. Test the finished enclosure, not an uncovered bench Pi alone.

## Production power checks

Run on the Pi, from the project checkout:

```sh
python3 scripts/pi-production-power.py --diagnose
python3 scripts/pi-production-power.py --plan --profile waveshare-25w-pi5
```

Both commands are read-only. The helper reports Pi model, active USB current allowance, device-tree power information, current/past throttle flags, temperature and input voltage when available. **It cannot measure total 5V or USB current.** The PMIC readings omit those loads; a voltage reading alone does not establish spare capacity. See [Raspberry Pi power documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply).

The named production chain and guarded apply command are in [production.md](production.md#the-garden-pis-production-power-profile). Normal MVP commissioning does not change boot power settings. Neither diagnostics nor an apply success certifies an outdoor electrical installation.

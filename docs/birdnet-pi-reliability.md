# BirdNET and Pi reliability notes

Checked against BirdNET-Go release **20261014**; UGREEN/Clippy research updated on 22 October 2026. These are failure modes worth checking, not measured failure rates. The installed hardware has not been tested. Start with `python3 scripts/commission-pi.py --diagnose` on the Pi; it is read-only. Use the [AI setup workflow](ai-setup.md) for its guarded SSH transport and bounded recovery.

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

## UGREEN 30724 and Clippy: compatibility and noise

The selected pairing is supported by a [published BirdNET-Go/Pi 5 build using US205 / article 30724 and a 3.5 mm Clippy](https://github.com/arnegiacomo/fugleramme/blob/main/docs/hardware.md). There is no evidence here of a general incompatibility; clean audio on this particular unit remains a physical acceptance check.

### Buy and connect the exact variants

- **UGREEN US205 / 30724:** two separate sockets; the **pink TRS socket is the mono microphone input**, green is headphone output. UGREEN explicitly excludes TS and TRRS microphones for this input. [Manufacturer specifications](https://fr.ugreen.com/products/ugreen-carte-son-externe-adaptateur-usb-audio-jack-3-5mm).
- **Ordinary mono Clippy, 3.5 mm TRS:** its stereo-shaped plug carries the same mono signal on tip/ring and needs plug-in power. Do not substitute Smart Clippy/TRRS or XLR, or add a smartphone adapter to this pairing. [Micbooster's variants](https://micbooster.com/product/clippy-em272-microphone/).
- **Bias remains an unverified specification:** the UGREEN manufacturer page does not state microphone bias voltage/current. USB bus power alone does not establish it. If routing and capture controls are correct but real sound is absent or unusually weak, verify the exact adapter revision with the supplier or a competent bench test before replacing software.
- **For new orders:** our selected microphone is a complete mono TRS Clippy with the **EM272M capsule**, which adds RF suppression. Micbooster warns that some EM272Z1 users encounter interference near Wi-Fi radio transmitters. This suggests testing our Pi placement; it does not prove Pi Wi-Fi causes every buzz or that an existing Z1 needs replacing. Order the assembled Clippy, not a bare capsule. [Manufacturer RF information](https://micbooster.com/product/primo-em272-m/), [Clippy selection](https://micbooster.com/product/clippy-em272-microphone/).

### Microphone choice for new orders

For the Clippy route, select **Capsules: Single; Microphone: EM272M** on the [assembled mono Clippy page](https://micbooster.com/product/clippy-em272-microphone/?attribute_pa_microphone=em272m&attribute_pa_single_2_4_matchedcapsules=single). Confirm the selected variant in the basket; do not rely on the generic EM272 product title or a stale price/stock indication. The illustrated list retains this route provisionally; the complete UGREEN pairing is not a measured winner over AudioMoth. Use a fitted windshield and rain shelter.

The [AudioMoth USB Microphone](https://www.openacousticdevices.info/product-page/audiomoth-usb-microphone) explicitly supports Linux/Raspberry Pi and replaces the separate analog interface. Its [USB firmware/settings](https://www.openacousticdevices.info/usb-microphone) need initial verification at 48 kHz with appropriate gain; our installer does not currently manage those device-specific settings. It is a legitimate first-choice candidate when minimizing separate connections and interface compatibility questions, not only a fallback after Clippy fails. That simpler hardware path is not proof of better audio or measured reliability. Its USB case is splashproof rather than the separate AudioMoth IPX7 case; shelter is still required. [Manufacturer case distinctions](https://www.openacousticdevices.info/audiomoth).

The acoustic reason to consider Clippy is its [EM272M capsule specification](https://micbooster.com/product/primo-em272-m/): 80 dB SNR, 14 dBA self-noise and -28 dBV/Pa sensitivity. The [AudioMoth USB 1.0.1 datasheet](https://github.com/OpenAcousticDevices/Datasheets/blob/main/AudioMoth_USB_Microphone_1_0_1_Datasheet/AudioMoth_USB_Microphone_1_0_1_Datasheet.pdf) lists its built-in microphone at 63 dBA SNR and -38 dBV/Pa. These are microphone specifications, not a matched end-to-end Pi recording test; do not claim the Clippy/UGREEN system is 17 dB quieter or detects more birds. Clippy also permits a small remote capsule outside the enclosure while its interface remains sheltered. AudioMoth's electronics must be placed with its built-in microphone, or it can use an external electret microphone through its documented 3 V bias input. External microphone operation is a separate configuration to validate, not an already-tested third package.

The AudioMoth datasheet specifies average USB current of 18–22 mA across its sample-rate range under its stated firmware/test conditions; this is not a guaranteed startup peak. Both candidates need a physical comparison if quiet-call performance determines the purchase: same position, conditions, sample rate and comparable signal levels, with no live test detections entering the garden's real counts. AudioMoth's persistent settings make configuration a one-time commissioning task, not necessarily recurring human work.

A Clippy plus RØDE AI-Micro would add documented plug-in power, but [RØDE does not guarantee Linux functionality](https://help.rode.com/hc/en-us/articles/9028082796175-Are-R%C3%98DE-USB-Products-Supported-on-Linux-Computers). That is not enough evidence to replace the inexpensive interface speculatively. The AI-Micro's [Stereo mode does not supply plug-in power](https://rode.com/en-us/products/ai-micro); a mono Clippy's TRS plug must not be mistaken for a stereo microphone. No alternative has been physically tested for this project.

### What people actually reported

| Evidence | Finding and limit |
|---|---|
| [BirdNET-Pi #591, March 2026](https://github.com/Nachtzuster/BirdNET-Pi/discussions/591) | Pi 4 + UGREEN + Clippy EM272Z1 had harsh interference. USB-over-Ethernet worsened it; battery power did not fix it. The reporter improved results by removing the extender, using a black USB 2 port and rerouting cables. These were combined changes, not proof of one cause. |
| [BirdNET-Go #2541, March 2026](https://github.com/tphakala/birdnet-go/discussions/2541) | Users reported opposite Pi 4 versus Pi 5 noise comparisons. This supports checking individual installations, not declaring the Pi 5 unsuitable. Do not turn anecdotal soldered grounding modifications into our setup procedure. |
| [BirdNET-Go #586, April 2025](https://github.com/tphakala/birdnet-go/issues/586) | A UGREEN appeared in Linux USB inventory but disappeared from BirdNET after an update. The issue was closed through an installer fix. Historical evidence for checking container capture access separately; not a known defect established in our pinned October 2026 release. |

BirdNET-Pi reports inform the physical audio chain only. Do not copy that application's old scripts or audio configuration into BirdNET-Go.

### Assistant-led physical audio acceptance

The assistant operates the software; the installer connects hardware, makes a test sound and confirms playback. This procedure supplements commissioning; it is **not an implemented automatic noise-calibration feature**.

On a fresh installation, BirdNET listens only on the Pi's loopback interface. The local assistant must arrange a temporary authenticated SSH forward from an available local loopback port (for example `127.0.0.1:18080`) to the Pi's `127.0.0.1:8080`, using the already-confirmed host identity and existing credential route, then open that local address. The main setup manager does not create this tunnel automatically. Do not rerun the fallback installer or expose BirdNET publicly just to listen.

1. **Establish a simple baseline.** Use the intended PSU and direct Clippy → pink input → UGREEN → Pi connection, initially on a black USB 2 port. Keep the capsule/audio lead clear of the Pi, fan and power wiring. Use the adapter's existing lead first; try a short shielded USB extension if needed for separation. Avoid USB-over-Ethernet in the MVP baseline. These are testable starting choices, not guaranteed cures.
2. **Verify the input, not playback controls.** Inspect the actual capture device, stable ID, 48 kHz configuration and available capture mute/gain controls. Do not impose 100% gain or assume all revisions expose the same mixer names. Preserve existing settings before adjusting. If direct ALSA diagnosis is needed, first account for BirdNET owning the device; a busy-device error alone does not mean hardware failure.
3. **Listen before declaring success.** Use BirdNET's local live audio/spectrogram for quiet ambience and a short spoken phrase or rustle near the mic. Confirm a corresponding level change and intelligible sound, without persistent buzzing, clipping or flat silence. Software capture/inference health can advance while the analog microphone is silent or noisy. Any temporary test recording stays local and out of support reports; routine clip export stays off.
4. **Compare under real conditions.** Repeat with normal network traffic and the fan running. If noisy, change one factor at a time: position/cable routing, USB port, then observed capture gain. Compare Ethernet only when a working wired management route is established; never disable the sole SSH network connection. Persistent USB resets call for the existing power diagnostics, not a blind power-limit override.
5. **Verify recovery and record evidence.** With the installer present, test USB unplug/replug and a Pi reboot; recheck the actual source, audible input and advancing inference. Save adapter/mic variant, selected ID, settings, outcomes and unresolved symptoms in the private commissioning notes. Physical audio acceptance remains pending until someone has heard this equipment. A real garden bird and delivery to Songsketch are separate checks.

The existing commissioner already discovers capture devices, prefers a stable ID and verifies configuration plus advancing inference. It does **not** measure microphone bias, calibrate hardware gain, certify interference-free audio or validate the enclosure. The ARM64/RTSP lab result cannot replace this test.

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

# Start here, garden keeper

Songsketch has three everyday parts: the garden Pi hears birds, the indoor server remembers them, and the painting page draws approved portraits. The same application supports the MacBook MVP and the later dedicated-host installation.

The visual [setup field guide](../guide/index.html) works from this folder, including without an internet connection. Keep the whole project folder together so its artwork and instructions remain available.

## First run on the Mac

1. Open the project folder in Finder and launch **Start Songsketch.command**. Keep the startup window open; it gives the local server address and operator-token instructions.
2. Open [the running setup guide](http://localhost:8765/setup), then [the garden dashboard](http://localhost:8765/dashboard). Use the local operator token to unlock the dashboard. The browser does not need a GitHub account to run the downloaded application.
3. Use **Send a test bird** and open [the painting page](http://localhost:8765/). Tests are labelled and excluded from real bird counts and missing-artwork emails.
4. Keep the Mac awake during the MVP. A sleeping or powered-off Mac cannot receive events, serve the painting or send reports at that moment.

The launcher checks for Python 3.9 or later. If a suitable Python is already installed, installing developer tools again is unnecessary. Read any startup error and follow the project README for the supported prerequisite route.

## Prepare and connect the Pi

Use the Pi kit’s suitable mains power supply for the first indoor test. Connect the Clippy microphone to the USB sound card’s microphone input, and connect the sound card to the Pi.

Check the supplied microSD before erasing it. A supported, working 64-bit Raspberry Pi OS can be reused. If the card is blank, unsupported, or needs a headless provisioning route, Raspberry Pi Imager can write a supported image and configure the account, network and SSH. **Writing an image replaces the card’s contents.** A preloaded OS does not mean BirdNET-Go or Songsketch is installed.

On the Mac, keep Songsketch running, open the project folder in Finder and double-click **Pair Garden Pi.command**. It opens the included helper in Terminal.

If you prefer an existing terminal, run `bash scripts/pair-pi.sh` from the project folder.

The helper prompts for the real Pi address, SSH account and server connection. It copies the server pairing configuration privately over SSH, so you do not need to copy a token by hand. Read the proposed changes before confirming. The Pi must use the Mac’s local-network address; `localhost` on the Pi points back to the Pi.

Read [the Pi instructions](pi-setup.md) for the supported OS checks, what the installer changes and local diagnostics. Select the actual USB microphone in BirdNET-Go’s setup; audio-device names depend on the hardware attached.

## Verify a real bird

A successful rehearsal proves local playback, not the microphone. Check the Pi heartbeat, audio capture and recognition health separately. Wait for a real detection and confirm its species and time appear in the history and the matching approved painting plays.

Briefly disconnect and reconnect the network, then restart the services and repeat the check. Confirm queued detections and reports arrive without duplicate counts. These are hardware acceptance checks to perform on your installation; the guide’s checkmarks do not run them automatically.

## Day to day

- **Birds you’ve heard:** detection history and portrait coverage. Counts are recognition events, not numbers of individual birds.
- **The art table:** missing portraits, approved references and optional AI jobs. New artwork stays a draft until reviewed; still-art approval and animation readiness are separate.
- **Keeping well:** recorded issues, health checks, backups and email retries. Reports upload automatically when connected. A support-report download is also available.
- **Garden settings:** the site name, garden timezone, deployment profile and optional email/AI settings. Email notifications cover missing artwork in this release; operational issues appear in the dashboard. Change credentials from the server’s local dashboard. Saved secrets are not shown back to the browser.

Core playback, stored history and routine recovery do not require an AI key. Optional jobs run only when deliberately started and can incur provider charges. An AI diagnosis explains a fault and proposes next steps; it does not execute arbitrary repair commands.

## When something goes quiet

A quiet garden is normal. Check actual equipment health before treating silence as a fault. While the server is unreachable, a powered Pi retains pending reports and retries after connection returns. A local Pi report download remains available through the documented diagnostics route.

The server handles defined routine maintenance and retains unresolved issues. Its operating-system supervisor can restart a crashed application; no application can send a report from a host that has lost power. Keep the last painting available while investigating interruptions.

## Moving beyond the MacBook

The [dedicated Linux host guide](production.md) explains migration using the same application and data. Changing the profile label alone does not install or move services. Migration, backup restoration, unattended reboot recovery and sustained operation still need verification on the selected machine. Permanent outdoor power, weatherproofing and network installation are separate hardware commissioning work.

Keep this guide with the software release it describes. The [README](../README.md) records the current implementation and verification status.

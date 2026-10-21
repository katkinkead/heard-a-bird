# Songsketch 0.2.0 — Finchley handles the wiring

The illustrated guide is now a control panel for AI-led setup. It gives a local terminal-capable assistant the project context, existing implementation, setup interfaces and recovery instructions. The assistant owns the software work; the human supplies physical connections, missing credentials, SSH identity confirmation and necessary permissions.

- A managed bootstrap creates the app folder, starts the supervised server and opens the guide with a single-use private session. Existing installations and other running services are preserved.
- The guide shows actual setup checkpoints, SSH trust, installation progress, microphone selection, test playback and diagnostic/recovery actions. Navigation no longer marks work complete.
- The guarded Pi helper provisions the pinned BirdNET-Go release, garden location, time, capture input, model, stored history and buffered delivery. Success requires live capture, advancing inference, readable history, server acknowledgement and a healthy relay scan.
- Saved checkpoints and redacted diagnostic packets tell the local AI how to diagnose, repair within a retry limit, verify and resume. Read-only diagnostics cannot claim successful installation. Routine service recovery requires no paid AI key.
- The requested copy edits, headless-first parts guidance, lowercase “no quills”, final aftercare section and “a Saber Lily production.” footer are included. The five approved animations remain unchanged.

**Verification:** all 137 automated tests pass locally and cover local HTTP/authentication, managed startup/reuse/shutdown, mocked SSH commissioning, Pi API contracts, preservation, diagnostics and failure recovery. The guide’s private-session opening, handoff, test painting and desktop/mobile layout were checked in the browser. This release has not commissioned a physical Pi: real microphone quality, bird recognition, network/reboot behaviour and unattended use still need the friend’s equipment. No external email or paid AI request was made.

Give the local assistant `docs/ai-setup.md` or use **Give my AI the brief** in `guide/index.html`. It obtains this private repository or the supplied release and operates the existing software. **Start Songsketch.command** is an optional Mac launcher for the same managed bootstrap. A chat without local computer tools cannot perform SSH or installation.

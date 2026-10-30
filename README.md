# Heard a Bird

**A listening garden. A slowly painted bird.**

Heard a Birdy (originally Songsketch). Repository snapshot updated **30 October 2026**. The Python package, service names and existing data directories retain `songsketch` for installation compatibility.

A garden Pi recognises birds with BirdNET-Go. An indoor computer remembers what it hears and sends a slowly painted bird to a browser. Start with a MacBook; move the same application and history to a dedicated Linux computer later.

## Start here

Open the [illustrated setup guide](guide/index.html). Its short path asks for **the Pi’s name**, then **Connect my AI & set up**. Account, location and network fields are optional upfront; the assistant reuses saved settings, discovers the indoor server address and asks only for information it cannot determine. The kit list and headless Pi-preparation steps remain available if needed.

On first use, unzip the downloaded launcher and open it once. A supported local Codex or Claude Code installation, its normal sign-in, private project access and a prepared Pi are prerequisites. The assistant handles configuration and checks; the user supplies missing Pi credentials privately, confirms the Pi’s identity and handles physical connections. No API key is required for routine bird recognition or paintings.

A standalone HTML page cannot launch an assistant or SSH into the Pi. The one-time local launcher, operating-system permission and provider sign-in are real first-launch steps. The launcher explains missing prerequisites; it does not pretend to install them. You need authorised access to the [private repository](https://github.com/katkinkead/heard-a-bird), or an owner-supplied release ZIP with its local setup helpers. Running that ZIP does not require a GitHub account.

The assistant handles routine computer work. Its instructions live in [AGENTS.md](AGENTS.md) and [the repository setup procedure](docs/ai-setup.md), rather than a long prompt copied into the guide. If you already have the project open in a local assistant, ask it to follow that procedure.

## What you get

Robin, Goldfinch, Blue tit, Blackbird and Wren include their approved **75-second animations**, stored locally alongside a [45-bird finished-art reference library](artwork/index.html), the current style/animation guides and the retained status graphics. All 45 sequences, including the clarity improvements, are packaged in the approved branch experience with branch, single-bird and infographic views. The original five-species portrait player remains available separately; its catalogue has not been silently replaced. The server provides detection history, a playback queue, an idle repertoire, a dashboard, backups and bounded recovery. Routine playback and maintenance need no AI API key. The local setup assistant uses your existing provider account. Optional dashboard AI diagnosis and artwork tools use separately configured API credentials; missing-art email needs SMTP settings. Saving a recipient alone does not send or verify email.

The Mac MVP must stay awake, powered and connected. A dedicated Linux host uses the same application with a different service profile. A Windows mini PC is not supported by this release. See [deployment and migration](docs/production.md).

Implemented software is not proof that the physical garden has been commissioned. Real microphone capture, a real bird, reconnect/reboot recovery and any configured email provider need checks on the installed equipment. The [feature map](docs/features.md) and [verification record](docs/verification.md) distinguish those boundaries.

## Useful places

- [Setup procedure for the local assistant](docs/ai-setup.md) · [Pi setup details](docs/pi-setup.md)
- [Architecture and access](docs/architecture.md) · [Feature map](docs/features.md) · [Verification](docs/verification.md)
- [Artwork and animation system](docs/artwork.md) · [Portable visual style guide](artwork/style-guide.html)
- [Dedicated host and migration](docs/production.md) · [Private remote viewing](docs/remote-viewing.md)
- [Installation audit: enclosure, weather, cooling and outstanding software gaps](docs/installation-audit.md)

The local control panel is `/setup`, the operator dashboard is `/dashboard`, and the painting is `/`. The default server port is 8765. Administrator actions accept localhost connections only; use the documented SSH tunnel for remote administration. Do not expose this port directly to the internet.

Application state stays outside Git: normally `~/Library/Application Support/Songsketch` on macOS, `~/.local/share/Songsketch` for manual Linux use, or `/var/lib/songsketch-server` for the dedicated service. The managed application is in `app/` within that directory; history and private configuration are preserved separately from releases.

## Try a simulated garden

Open **Open simulated garden.command** on a Mac, or run `python3 scripts/simulate.py` from this project. This starts an isolated local rehearsal, with its own history and no outgoing email, paid AI or Pi connections. Use its scenario buttons to test detections, retries, missing art, failures and recovery. Each run records expected versus actual results; add visual notes and export a report when something looks wrong.

See [the QA walkthrough](docs/simulation.md). Open **Review all 45 animations** inside the practice garden for ten-second checkpoints and a side-by-side comparison with each accepted portrait. The gallery waits for local preparation before beginning the full sequence; the live display follows the server clock and may catch up after a cold load.

Simulation tests the application; the final microphone, BirdNET recognition and physical network still need a real garden test. The repository includes a bug-report form for tracking reproducible findings.

## Development

Read [AGENTS.md](AGENTS.md) before changing the application. [CLAUDE.md](CLAUDE.md) uses the same instructions. Operate or extend existing features before proposing replacements.

The [real BirdNET validation](docs/birdnet-live-validation.md) records successful ARM64 recognition, API settings and relay delivery checks. The [release-validation plan](docs/release-validation.md) separates that evidence from the remaining SMTP/browser, varied-audio and virtual Linux installation tests. These are developer checks before handover, not extra steps in the illustrated setup journey.

```sh
python3 scripts/check-install.py
python3 -m songsketch.server
python3 -m unittest discover -s tests -v
```

Python 3.9 or newer is required. Routine playback needs no npm install or Docker on the Mac. The normal test suite uses local or mocked services. Developer-only BirdNET lab scripts can check a real disposable recogniser; neither suite makes paid AI requests or sends external email. Guide, software and approved assets are versioned together.

## Server-connected branch rehearsal

Open **Open branch rehearsal.command** for the isolated 45-bird growing-branch test. It uses the existing server and real authenticated ingest route with synthetic observations. See [the morning walkthrough](docs/branch-rehearsal.md) for arrivals, repeats, periods, faults and known release work. The original portrait player remains available.

## Branch content and remaining release work

The branch rehearsal now includes sourced facts for all 45 birds, separate regional/garden visitor badges, menu audio controls, a complete 45-species locally saved sound library with recording credits and Garden desk activity evidence. See [content, audio and verification](docs/branch-content-and-audio.md) and the [ordered remaining-work list](docs/remaining-work.md). Physical commissioning and the expanded release gate remain pending.

The complete branch experience is visually approved. The Garden desk now collects bounded browser fault reports and offers a ten-minute microphone-test exclusion window. [Recovery and rehearsal notes](docs/display-recovery.md) explain both, plus the reproducible simulated Pi sequence. Hardware commissioning and the longer release validation gates remain separate.

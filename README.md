# Songsketch

**A listening garden. A slowly painted bird.**

The garden Pi recognises birds with BirdNET-Go. A small indoor server keeps their history and serves approved, locally stored paintings to a browser. A MacBook provides the MVP; a dedicated Linux computer runs the same application for the permanent installation.

**Start by giving [the setup handoff](docs/ai-setup.md#copy-this-to-your-local-assistant) to a local terminal-capable assistant.** It handles the release, folders, server and supported Pi setup; the [illustrated guide](guide/index.html) is the human control panel for progress, permissions and physical tests. An ordinary cloud chat or an HTML file alone cannot execute this setup. Python 3.9 or newer is the server runtime dependency. Routine playback needs no npm install, Docker on the Mac or AI API key.

[Private GitHub project](https://github.com/katkinkead/songsketch) · [Friend’s short instructions](docs/friend-start-here.md) · [Verification record](docs/verification.md) · [AI orientation](AGENTS.md)

## The first five residents

Robin, Goldfinch, Blue tit, Blackbird and Wren are bundled with their approved **75-second** painting sequences. The artwork, drawing engine, style references and thumbnails are local. Playback uses the existing pressure-shaped marks, pigment fields and detailed finishing sequence; it makes no image-generation request.

The [art table](http://localhost:8765/dashboard#atelier) links to the [portable style guide](artwork/style-guide.html). New drafts cannot replace an approved bird automatically. Final-art approval and animation readiness are separate.

## Open the garden

1. Give a local assistant the [portable handoff prompt](docs/ai-setup.md#copy-this-to-your-local-assistant). It should discover an existing installation first, preserve its data and use this release's actual helpers. You do not need to manage project folders or copy a sequence of terminal commands.
2. Connect the garden hardware and provide the missing site/Pi details. Use a local private prompt for credentials, confirm the actual SSH host identity, and approve any operating-system action that needs you. A usable supported Pi OS is preserved; a blank or inaccessible card may need an explicitly approved first-boot/Imager step.
3. Follow the control panel as the assistant installs, verifies and diagnoses. A labelled test bird verifies the display; real capture, inference, a real detection and recovery are separate checks. The assistant should report the exact remaining human action, not declare untested equipment complete.

The Mac MVP must remain awake, powered and connected. For a permanent installation, the assistant handles supported [Linux service setup and migration](docs/production.md); hardware commissioning remains physical. Missing-art email and paid AI drafts are optional after the core garden works. BirdNET-Go with BirdNET v2.4 does not need an OpenAI/API key.

The repository and release are private. Existing authorised GitHub access or the owner's supplied ZIP is sufficient; running that ZIP does not need a GitHub account. No personal GitHub token belongs on the Pi. If a local assistant is unavailable, the existing **Start Songsketch.command** and **Pair Garden Pi.command** launchers remain a manual fallback; [Pi setup](docs/pi-setup.md) documents their limits.

### Developer start

```sh
python3 scripts/check-install.py
python3 -m songsketch.server
```

Visit `/setup`, `/dashboard` and `/`. The server listens on port8765 on the local network; administrator actions accept localhost connections only. For remote administration use an SSH tunnel. Do not forward the port to the public internet. See [architecture and access](docs/architecture.md). For private viewing away from home, follow [remote viewing](docs/remote-viewing.md); the MVP is local-network-only until that separate connection is configured.

## What is built

| Part | Implementation | Verification boundary |
|---|---|---|
| Setup guide | Illustrated local control panel, project links and hardware checks alongside the assistant workflow | Only verified helper evidence is marked; diagnostic completion is separate from installation |
| AI-led setup | Managed local bootstrap, guarded setup CLI/API, explicit SSH trust, Pi commissioning and diagnostic context | Requires an authorised local assistant; real Pi, sudo, microphone and network acceptance remain |
| Mac launch | Double-click launcher, Python check, sleep inhibitor; optional per-user background service | Local server tested; installing a persistent service on a friend’s Mac still needs commissioning |
| Pi relay | Stored-history catch-up, stable event IDs, durable outbox, heartbeat, protected offline reports | Mock BirdNET + real localhost receiver tests; actual Pi/microphone not attached |
| Server | SQLite history, confidence filter, retry deduplication, playback queue, weighted idle repertoire, SSE | Automated tests and browser test bird |
| Display | Five packaged paintings, subtle truthful status, brushstroke progress, last-frame retention on disconnect | Five final-frame/fidelity checks and integrated browser playback |
| Dashboard | History, counts, portrait coverage, health, settings, diagnostics and review queue | Browser interactions and HTTP tests |
| Missing-art email | One durable notice per new qualifying species; retries and visible uncertain-delivery state | SMTP is mocked in tests; configure and verify a real mail account during setup |
| Maintenance | Health watchdog, OS service profiles, report grouping, bounded logs, backups and migration export | Local recovery tests; host reboot/power tests remain |
| Optional AI | Explicitly triggered diagnostic, art and style drafts; animation **authoring proposals**; review before artwork approval | Mocked API tests; provider access and real paid results require the friend’s key |
| New-bird animations | Existing prepared birds preview locally; AI can propose registration and timing | A new species still needs authoring and milestone validation. An API key does not make a finished approved animation |
| Dedicated host | Linux systemd installer, same server/data, migration and rollback instructions | Target mini PC and outdoor installation are not yet commissioned |

See [verification.md](docs/verification.md) for exact checks and limits. “Implemented” does not mean the microphone, network, email provider or eventual mini PC has been tested on your equipment.

## Where everything lives

| Folder | What it holds |
|---|---|
| `guide/` | The friendly HTML front door, navigation and project/release links |
| `songsketch/` | Server, SQLite records, queue, maintenance, optional AI jobs and supervision |
| `static/` | Painting display and operator dashboard |
| `pi/` | BirdNET relay, private configuration example and pinned API contract |
| `artwork/` | Approved catalogue, five animations, thumbnails, retained sources and portable style/painting system |
| `scripts/` | Mac/Pi/Linux setup, preflight, artwork packaging and restore helpers |
| `docs/` | Architecture, installation, migration, API, feature status and verification |
| `tests/` | Local integration, persistence, recovery, auth, AI/mail mocks and artwork checks |

Runtime data stays **outside Git**: `~/Library/Application Support/Songsketch` on macOS, `~/.local/share/Songsketch` for a manual Linux run, or `/var/lib/songsketch-server` for the dedicated Linux service. `SONGSKETCH_DATA_DIR` overrides it. This contains the SQLite database, protected configuration, secret file, rotating logs, seven backup snapshots and optional drafts. Secrets are never included in support reports or migration exports.

The AI bootstrap keeps a managed application copy in `app/` under that private directory and records its setup state there. It preserves an existing copy rather than silently upgrading it. Bootstrap starts the current session's supervised server; persistent login/boot services are separate deployment steps. The assistant uses [the documented helper interface](docs/ai-setup.md#interfaces-for-the-assistant) and opens the local guide without putting the durable setup credential into chat.

Counts mean qualifying BirdNET detection records, not individual birds. Each station/event pair is counted once. All new records are stored even when display cooldown suppresses another painting. Monthly boundaries use the garden’s timezone, Europe/London by default. Current retention is two years for detection records, seven days for test events and 30 days/up to5000 uploaded reports. BirdNET’s later false-positive edits/deletions do not currently retract imported history.

## MVP and dedicated-host profiles

The **MacBook MVP** runs while its owner is logged in and the Mac is awake. `Install Mac Background Service.command` optionally installs a launchd service; have the assistant stop the existing session’s supervisor first. It does not make a closed or powered-off Mac reachable.

The **dedicated Linux profile** uses `scripts/install-server-linux.sh`. It is separate from `scripts/install-linux-service.sh`, which installs the **Pi relay** service. Follow [production.md](docs/production.md) for migration, SSH administration, backup restoration, restart and power checks. Windows mini PCs are not supported by this release.

The exact CanaKit listing in the shopping list is ASIN **B0CVQRCMLY**, the4GB Essentials kit pictured with32GB storage. Its listing names Raspberry Pi OS but does not confirm an exact preloaded image. CanaKit’s current64GB kit explicitly ships64-bit Raspberry Pi OS; that is a different variant. The guide therefore makes imaging conditional and still covers account, Wi-Fi and SSH setup. Sources: [exact listing](https://www.amazon.co.uk/dp/B0CVQRCMLY/), [CanaKit64GB variant](https://www.canakit.com/canakit-raspberry-pi-5-starter-kit-red-white-64gb.html), [Raspberry Pi setup](https://www.raspberrypi.com/documentation/computers/getting-started.html).

## Working on Songsketch with AI

For installation or recovery, start with [the AI setup handoff](docs/ai-setup.md). Read [AGENTS.md](AGENTS.md), this README and the actual implementation before changing anything. [CLAUDE.md](CLAUDE.md) points to the same project instructions. The feature map in [docs/features.md](docs/features.md) helps an assistant distinguish work already implemented from an idea or a hardware check. The requested “Saber Lily already considered it :)” acknowledgement is used only when a specific source supports it.

Earlier design decisions are retained in [integration-plan.md](integration-plan.md), [dashboard-requirements.md](dashboard-requirements.md) and [maintenance-requirements.md](maintenance-requirements.md). The running code and verification record establish current status. The original published Claude artifact has not been modified; its reviewed setup flow has been rebuilt here alongside the software.

## Checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check-install.py
```

Tests make no paid AI requests and send no external emails. Network tests bind loopback only. Release packaging excludes runtime data, credentials, development caches and Git internals. The setup guide and software are versioned together.

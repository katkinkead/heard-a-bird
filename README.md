# Songsketch

**A listening garden. A slowly painted bird.**

The garden Pi recognises birds with BirdNET-Go. A small indoor server keeps their history and serves approved, locally stored paintings to a browser. Your MacBook is the first server; a dedicated Linux mini PC can take over later using the same application and data.

**Start with [the illustrated setup field guide](guide/index.html).** Keep the whole downloaded folder together and double-click **Start Songsketch.command** on the Mac. The guide opens at [localhost:8765/setup](http://localhost:8765/setup). Python 3.9 or newer is the only server runtime dependency; the launcher checks for it. No npm install, Docker or API key is needed on the Mac.

[Private GitHub project](https://github.com/katkinkead/songsketch) · [Friend’s short instructions](docs/friend-start-here.md) · [Verification record](docs/verification.md) · [AI orientation](AGENTS.md)

## The first five residents

Robin, Goldfinch, Blue tit, Blackbird and Wren are bundled with their approved **75-second** painting sequences. The artwork, drawing engine, style references and thumbnails are local. Playback uses the existing pressure-shaped marks, pigment fields and detailed finishing sequence; it makes no image-generation request.

The [art table](http://localhost:8765/dashboard#atelier) links to the [portable style guide](artwork/style-guide.html). New drafts cannot replace an approved bird automatically. Final-art approval and animation readiness are separate.

## Open the garden

1. Extract the release folder somewhere you will keep it. On macOS, double-click **Start Songsketch.command**. If macOS asks how to open a downloaded script, open it with Terminal after reviewing its source. The startup window displays your private setup code.
2. Follow the guide and unlock the dashboard using that code. Send a test bird and open the painting page. Tests are labelled and excluded from real counts and emails.
3. Prepare the Pi’s OS, account, Wi-Fi and SSH. Reuse a suitable preloaded 64-bit OS; do not erase a working card just because it came with the kit. Open **Pair Garden Pi.command**, enter the Pi address and follow its prompts. It transfers the Pi credentials over SSH and installs the bundled relay and pinned BirdNET-Go version.
4. Select the actual microphone and Dorset location in BirdNET-Go’s first-run setup. Verify audio, recognition, a real detection, and reconnect recovery. The guide explains what each check proves.
5. Add an email contact and SMTP settings if you want missing-portrait notices. AI settings are optional. Leave the Mac plugged in with its lid open during the MVP.

The downloaded application works without GitHub access. The repository and release are private: the owner can provide the ZIP directly or grant the friend repository access. No personal GitHub token is installed on the Pi.

### Developer start

```sh
python3 scripts/check-install.py
python3 -m songsketch.server
```

Visit `/setup`, `/dashboard` and `/`. The server listens on port8765 on the local network; administrator actions accept localhost connections only. For remote administration use an SSH tunnel. Do not forward the port to the public internet. See [architecture and access](docs/architecture.md).

## What is built

| Part | Implementation | Verification boundary |
|---|---|---|
| Setup guide | Illustrated local HTML, eight steps, actual project links, checkmarks and live-server link | Desktop/mobile browser checks; real hardware steps remain human checks |
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

Counts mean qualifying BirdNET detection records, not individual birds. Each station/event pair is counted once. All new records are stored even when display cooldown suppresses another painting. Monthly boundaries use the garden’s timezone, Europe/London by default. Current retention is two years for detection records, seven days for test events and 30 days/up to5000 uploaded reports. BirdNET’s later false-positive edits/deletions do not currently retract imported history.

## MVP and dedicated-host profiles

The **MacBook MVP** runs while its owner is logged in and the Mac is awake. `Install Mac Background Service.command` optionally installs a launchd service; stop the foreground run first. It does not make a closed or powered-off Mac reachable.

The **dedicated Linux profile** uses `scripts/install-server-linux.sh`. It is separate from `scripts/install-linux-service.sh`, which installs the **Pi relay** service. Follow [production.md](docs/production.md) for migration, SSH administration, backup restoration, restart and power checks. Windows mini PCs are not supported by this release.

The exact CanaKit listing in the shopping list is ASIN **B0CVQRCMLY**, the4GB Essentials kit pictured with32GB storage. Its listing names Raspberry Pi OS but does not confirm an exact preloaded image. CanaKit’s current64GB kit explicitly ships64-bit Raspberry Pi OS; that is a different variant. The guide therefore makes imaging conditional and still covers account, Wi-Fi and SSH setup. Sources: [exact listing](https://www.amazon.co.uk/dp/B0CVQRCMLY/), [CanaKit64GB variant](https://www.canakit.com/canakit-raspberry-pi-5-starter-kit-red-white-64gb.html), [Raspberry Pi setup](https://www.raspberrypi.com/documentation/computers/getting-started.html).

## Working on Songsketch with AI

Read [AGENTS.md](AGENTS.md), this README and the actual implementation before building. [CLAUDE.md](CLAUDE.md) points to the same project instructions. The feature map in [docs/features.md](docs/features.md) helps an assistant distinguish work already implemented from an idea or a hardware check. The requested “Saber Lily already considered it :)” acknowledgement is used only when a specific source supports it.

Earlier design decisions are retained in [integration-plan.md](integration-plan.md), [dashboard-requirements.md](dashboard-requirements.md) and [maintenance-requirements.md](maintenance-requirements.md). The running code and verification record establish current status. The original published Claude artifact has not been modified; its reviewed setup flow has been rebuilt here alongside the software.

## Checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check-install.py
```

Tests make no paid AI requests and send no external emails. Network tests bind loopback only. Release packaging excludes runtime data, credentials, development caches and Git internals. The setup guide and software are versioned together.

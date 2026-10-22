# Try a garden without the Pi

Open **`Open simulated garden.command`** in the project folder. It starts a private practice garden at **http://127.0.0.1:8766/simulation** and opens it already unlocked. Keep its Terminal window open while testing; Control-C stops it. Python 3.9 or newer is the only runtime requirement. Opening the launcher again reopens the same simulator.

The ordinary server remains on port 8765. The simulator uses a separate marked folder, database and login cookie. It cannot send external email, call paid AI, SSH into the Pi, launch a setup assistant or change the real garden's configuration. No Pi, microphone, provider account or email settings are needed.

## What to try

Choose a moment, press **Try this moment**, and watch the painting or open the operator dashboard. Each scenario starts with fresh synthetic garden data; its earlier report remains available. The familiar-bird example starts the approved Robin animation. Let the full 75 seconds play before assessing its finish.

- **Familiar bird and message retry:** check the selected painting, observation counts and duplicate handling.
- **Visitor without art:** a deliberately fictional QA species creates a notification in the local simulation inbox. Nothing is emailed. The existing painting remains.
- **Pi disconnect and reconnect:** the fixture ages a heartbeat beyond the real timeout, then can deliver a fresh heartbeat. Disconnect can stay visible for inspection.
- **Capture or recognition failure:** the Pi remains connected but listening becomes unavailable, with a diagnostic report.
- **Power and heat warnings:** synthetic telemetry exercises the same validated metadata and warning path. It neither measures real power nor changes firmware, cooling or shutdown behaviour.
- **Recovery:** current faults clear after healthy evidence and recovery reports. Historical under-voltage evidence remains historical.
- **Busy chorus and idle:** seeded observations include a duplicate and a low-confidence record. A fixture clock jump ages the replay queue so the real idle selector can be checked without waiting several minutes.

The dashboard counts these records in its isolated database so the real counting and notification logic is exercised. They are never presented as real hardware verification. Test the filtering and diversity views there too; counts describe synthetic qualifying events, not individual birds.

## Leave useful feedback

Automatic results show an expected value and the actual observation. A passed assertion means that particular server behaviour matched, not that the painting looks good. Visual review stays separate from those checks; describe what you saw in the notes. Note the species, the approximate second in the animation, and whether the issue concerns stroke flow, pace, detail, composition or a status mark.

Add those observations and download the report. It includes the scenario, seed, generated events, expected/actual checks, final simulated state and sanitized diagnostics. Known credentials and common secret patterns are redacted. Review free-text notes before sharing; redaction cannot identify every personal detail. Reports remain local until you choose to send one. The latest downloaded report is saved privately as `latest-simulation-report.json`; up to 100 scenario records are retained in `simulation-runs/`.

If the simulator stops responding after this page has received a successful status response, **Download report** and **Copy report** still work. This offline export contains the application version, the last successful status time, cached run checks, your notes and basic browser observations. It is marked `offline_snapshot: true`; newer actions may be absent. It excludes private configuration and server diagnostics and is downloaded locally, rather than saved back to the stopped server. Keep the page open: its cached evidence is held only for that page session. A fresh page that has never connected cannot produce an offline report.

## Candidate animation review

The standard simulator uses the five connected playback animations. A separate, explicit review launch can include the candidate 45-bird catalogue:

```sh
python3 scripts/simulate.py --review-animations --data-dir /tmp/songsketch-candidate-review --port 8767
```

Open the dashboard's painting test selector to choose a candidate species. The additional forty animations are awaiting visual review, including recent feedback about clarity and fragmentation. Preview eligibility is changed **only in the simulator's memory**. Neither the candidate file's approval flags nor the live five-bird catalogue is changed. A timing check or a complete rendered image does not approve the artistic result.

For a complete candidate sequence, use [the animation review gallery](../artwork/review.html). Some candidates have a noticeable cold preparation step; on the live display that can consume part of the event's 75-second window. The review gallery starts its full sequence after preparation. This timing difference is recorded as a limitation, not hidden by the simulator.

## For the local assistant

Use `python3 scripts/simulate.py --help`. The default data folder is `~/Library/Application Support/Songsketch Simulation` on macOS or `~/.local/share/Songsketch Simulation` on Linux. `SONGSKETCH_DATA_DIR` is not used to choose this folder. The helper rejects the real garden folder, overlapping paths, non-empty unmarked folders and symlinked runtime files. Do not delete or reset the real garden to make a scenario pass.

`--data-dir`, `--port`, `--no-open`, `--review-animations` and the explicit `--candidate-catalogue` option are supported. `--no-open` does not print a login ticket; rerun without it to open the browser securely. No persistent service is installed. If the chosen port belongs to another server, choose another port rather than stopping that server. Reopening refuses a changed catalogue; use a separate folder/port or stop that simulator before switching.

The loopback-only routes are:

| Route | Behaviour |
| --- | --- |
| `GET /api/simulation/status` | Mode, scenario definitions, newest-first recent runs, local captured notifications and display links |
| `POST /api/simulation/run` | `{ "scenario": "known-bird", "seed": 20261022 }`; returns `{ "simulation": true, "run": ... }` |
| `GET /api/simulation/report?run_id=...` | Download one run, or omit `run_id` for retained runs |
| `POST /api/simulation/report` | `{ "notes": "...", "run_id": "optional" }`; saves and downloads the sanitized report |

These routes require the simulator's local session. The launcher uses a short-lived, single-use opening ticket; admin and station tokens are never put in the page or report. Synthetic detections, heartbeats and diagnostics pass through the production HTTP ingestion handlers with private simulator credentials. The captured-email sink replaces SMTP at the instance boundary, and AI and commissioning objects expose no working remote actions. The safe background loop only refreshes synthetic heartbeats and ticks playback.

Seeds repeat the generated burst order. Timestamps, run IDs and the real idle selector's random choice can vary; those actual observations are recorded. Fixture clock jumps are identified explicitly. This verifies software paths under controlled inputs, **not** BirdNET accuracy, real audio, Pi temperatures, network outages or unattended hardware recovery. Those still need the physical checks in [verification.md](verification.md).

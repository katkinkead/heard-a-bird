# Verification record — 22 October 2026

This is a locally verified MVP, not a commissioned garden installation. The source, guide, 45 finished-art references, five approved animations and forty completed review candidates travel together in the v0.4.0-mvp package. Review candidates are not automatically approved for live playback. Earlier verification is retained below as historical evidence.

## Original 0.1.0 verification (historical)

- **78 automated tests** on macOS with Python3.9.6, also passing from a freshly extracted release folder. The same78 tests and preflight/shell checks pass independently on GitHub’s macOS and Ubuntu runners with Python3.11 ([verified run](https://github.com/katkinkead/songsketch/actions/runs/39594296811)). Tests cover actual loopback HTTP between the Pi relay and Songsketch, event and report persistence, lost acknowledgements, pagination/catch-up, confidence/time validation, monthly timezone boundaries, queue/cooldown separation, session logout, origin/credential separation, redaction, concurrency, backup contents and authenticated migration export.
- The Pi tests use a simulated BirdNET API matching the pinned20261014 source contract; they do not record audio or run a real BirdNET model.
- Email tests use a fake SMTP server/client. They verify one missing-art notice per species, retry after pre-send failures, and an explicit review state when delivery is uncertain.
- AI tests use mocked OpenAI responses. They verify that credentials and explicit paid-request confirmation are required, daily job limits apply, provider errors do not auto-retry, interrupted jobs remain reviewable, and original approved birds/style are protected.
- Watchdog tests verify HTTP health failures, process ownership, backoff, restart limits, shutdown, occupied-port refusal and private rotating logs. A real-process test kills only its isolated owned server, confirms a replacement PID and recovered HTTP/history, then verifies parent shutdown leaves no child behind. The Mac launchd configuration passes `plutil` validation; shell installers pass `bash -n`. No background service was installed on this Mac as part of these checks.
- All five packaged animations load and complete at75 seconds. The retained source files and Robin benchmark are hash-checked. Final-frame comparison excludes the intentionally removed baked example status annotation; the bird/name/background comparison is recorded in `artwork/fidelity-validation.json`.
- Browser checks through the actual running application: guide navigation/checkmarks, repository link, dashboard login, test Robin, unchanged real counts, settings, profile/job limit, backup, diagnostic download, approved-art gallery and disabled AI controls without a key. Desktop and390px layouts were inspected; no dashboard console errors were seen.
- The integrated painting page was inspected in the Codex browser. It paints the selected bird and shows the small dynamic corner status. The wrapper preserves the last painting during connection failure.
- Local preflight confirms the five images/animations and all application entry points are present. JavaScript syntax checks pass.

The direct `file://` guide preview was blocked by browser URL policy; it was not bypassed. Its local relative links/assets were checked, and the same guide was exercised over the local server. The guide includes a file-mode path with no remote dependencies; the launcher opens the tested HTTP route.

Browser testing of the key-removal control stopped at its confirmation. No real AI key was configured. Credential removal is covered with disposable configuration in automated tests; the absent-key UI was checked read-only. No external email was sent and no paid AI request was made.

## Must still be checked on the actual installation

1. CanaKit card/OS, actual USB microphone and gain, BirdNET model setup and Dorset coordinates.
2. Real Pi service installation, real detections, Wi-Fi range, outage replay and Pi reboot.
3. The installation Mac’s permissions, background-service login/restart behaviour, lid/sleep behaviour and display browser.
4. A real SMTP delivery using the configured mail account and notification recipient.
5. Optional API account access, model availability and visual quality of actual paid drafts. An animation proposal is not a completed newly authored animation.
6. The selected mini PC, restored migration bundle, startup after power loss, sustained use and outdoor enclosure/power/environment.

The current guide reports actual helper evidence; it has no human checkmarks that imply hardware success. A successful setup simulation is excluded from real bird counts.

## 0.1.1 guide appearance update

The guide’s original illustrations, paper notes and bird navigation were checked in the running local application at desktop and narrow mobile widths. No horizontal overflow, broken images or browser console errors were observed. Step navigation and checkmark updates work, and the technical instructions and application behaviour are unchanged. The three equipment illustrations are embedded SVG symbols so the standalone HTML does not rely on cross-file SVG references. JavaScript syntax and package preflight pass. This appearance-only update does not add new hardware or provider verification.

## 0.1.2 guide flow and BirdNET readiness

Browser checks confirmed that Next marks only its current step finished, advances, and persists after reload; bird navigation changes the view without adding completion. The old checkbox is absent. Reset returned the preview to zero finished steps. Desktop and mobile layouts have no horizontal overflow. BirdNET readiness was reviewed against the pinned release’s source and manufacturer documentation, with primary links in `pi-setup.md`. Shell syntax, the unsupported-Mac installer guard, the 11 Pi tests and package preflight pass. The new arm64-userspace and capture-device checks still need execution on real supported Pi hardware; they do not certify audio quality. Private remote viewing is documented, not installed or verified.

## 0.2.0 AI-led setup and recovery

**137 automated tests pass locally on macOS/Python 3.9.6.** The combined suite includes 27 guarded-SSH tests, 22 Pi commissioning contract tests and 10 setup integration tests, alongside the 78 existing application tests. SSH is mocked except for the real local FIFO/process-lifecycle checks; the Pi API uses fixtures and loopback HTTP. No physical Pi was commissioned.

A real disposable bootstrap test copies the release to its managed app location, starts the supervised server, verifies the private setup API, reuses the healthy server on a second call, checks copied launchers/docs/artwork, and stops its owned server cleanly. Existing files, occupied foreign ports and mismatched credentials are preserved. No persistent host service was installed.

Security/repair tests cover single-use expiring browser tickets, local-origin/session boundaries, SSH fingerprint pinning, argument validation, password redaction without corrupting protocol states, non-finite JSON rejection, private secret transfer, bounded cancellation and retries, active remote-operation locks, and exact container/image/endpoint ownership before Pi changes. Successful installation evidence remains separate from a completed diagnostic operation.

Browser verification used a disposable loopback server and a test-only opening ticket. The ticket was consumed and removed from the URL; the guide enabled its controls, queued a labelled test Robin, rejected malformed input before SSH, preserved a changed address on re-probe, and showed recovery after a reserved `.invalid` test hostname failed. The diagnostic packet downloaded successfully. Aftercare and healthy-listening indicators remained hidden without equipment evidence. Desktop and narrow mobile layout checks, JavaScript syntax, shell syntax and package preflight pass. This does not verify real microphone quality, real species recognition, network/reboot recovery, optional email/paid AI, remote viewing or the final unattended host.

The local assistant is instructed to diagnose, make bounded safe repairs, verify and resume. This is a reusable operating procedure plus guarded software interfaces, not a promise that arbitrary hardware or third-party failures can heal themselves without physical access or permission.

## 0.3.0 repository handover, art library and health

**195 application tests and eight animation-import tests pass locally.** The suite includes guarded GitHub/assistant launch, custom data-directory propagation, executable-preserving ZIP generation using the actual guide JavaScript, setup API authentication/locking, reference-art availability and notification reconciliation, and power/thermal telemetry. Provider, SSH and hardware interactions use fixtures or mocks; local HTTP/process tests use isolated temporary directories.

The installer preflight verifies 45 references, five completed animations and 50 unique asset hashes, plus required guide/launcher entrypoints and registry/catalogue consistency. Its failure cases include tampered/missing assets, malformed metadata and path traversal. The 131-file import snapshot retains source hashes; unfinished files from the active art thread were not copied into playback. JavaScript, generated launcher and shell syntax checks pass.

The running guide was checked at desktop size: Step 0 shopping links and kit cards, ordered navigation, editable saved details and clearing, the private one-use opening ticket, and eight live component checks. The server/database alone appeared checked; absent microphone, inference, hardware and display evidence stayed unverified. The reference gallery loaded all 45 species. A requested 390px viewport remained at1180px in this preview, so this revision's narrow-screen rendering is not newly verified.

The production power helper has fixture tests for diagnostics, safeguards, idempotent changes and configuration preservation. No power setting, EEPROM, physical Pi or reboot was changed. Manufacturer evidence and the remaining PoE/USB-C compatibility checks are recorded in production.md and birdnet-pi-reliability.md.

No live email or paid model request was sent. Email requires configured SMTP, not just a recipient. A known final portrait without a completed animation is tracked separately and does not trigger a missing-art email. Tests do not certify physical recognition quality, long-term reliability, real email delivery, remote access or the eventual production power chain.

## 0.4.0 practice garden and completed-animation review

**215 application tests, eight artwork-sync tests and six JavaScript report tests pass locally.** The practice garden uses real loopback HTTP ingestion and the production store/playback logic with isolated synthetic data. Twelve scenarios cover detections, duplicate delivery, missing art, Pi loss/recovery, capture/inference failure, power/thermal reports and idle selection. SMTP is replaced with a local inbox; AI, SSH, installation and real-configuration writes are disabled. Tests cover authenticated access, separate cookies, protected runtime paths, report redaction/persistence, unique replay IDs and candidate eligibility held only in memory.

The guide welcome was dismissed, followed forward/back through setup and reloaded: it remained hidden while the parts checklist stayed available. Desktop and 390px layouts had no horizontal overflow. The simulator's familiar-bird, local-notification and Pi-disconnect scenarios produced passing expected/actual evidence in the browser. Earlier reports survived a restart. The display retained a visible simulated label. Its 390px layout also had no horizontal overflow.

After the simulator was stopped, the open page successfully downloaded an offline report containing three cached run records, a timestamp and visual notes. The downloaded JSON had `offline_snapshot: true` and excluded private configuration and diagnostics. Offline evidence is limited to the last successful response in that page session; unconfirmed later actions cannot be inferred from it. Six JavaScript tests verify this allowlist, redaction, bounded caching and the absence of a false visual pass.

The review gallery includes all 45 sequences; the original five and live catalogue remain byte-for-byte unchanged. Preflight checks 45 references, five live animations, forty review animations and 220 asset hashes. Source provenance freezes the completed snapshot separately from the fork's active fidelity work. Browser inspection of Long-eared owl verified 40-second and 75-second rendering, all 184,056 marks completed, and the side-by-side accepted-art comparison. Cold local preparation took 9.49 seconds in this browser. Seeking directly to completion can briefly block the UI; live replay follows its server clock and can skip opening strokes after cold preparation. The standalone gallery waits before playback, preserving its full 75-second review. These checks do not certify artistic likeness, fluidity on the eventual hardware or approval of the forty candidates.

An initial full test run exposed a path-normalisation error in a test fixture and a shared startup/recovery deadline in the real-process test. The fixture was corrected and each process phase now has its own bounded allowance; production recovery timing is unchanged. The final full application run passed all 215 tests. No physical Pi, external email or paid AI service was used.


## 0.4.1 real BirdNET API and audio validation

The actual pinned `20261014` ARM64 container ran on a separate local Linux VM with the stock BirdNET v2.4 ONNX INT8 model. Real cookie/CSRF PATCH/readback checks passed for the common commissioning settings, including after a real container restart. The production advancing-inference check passed. Repeated upstream Tawny Owl audio produced ten stored detections; the unchanged production relay delivered exact normalized IDs/values into a temporary real Songsketch HTTP server, with correct counts, no duplicates on re-poll, an empty outbox and one pending unsent notice in an intentionally empty art catalogue. See [the evidence and run procedure](birdnet-live-validation.md).

This run found a real Python 3.9 incompatibility with Go's fractional timestamp precision; the parser fix is covered using the observed timestamp. Regression tests also cover settings rollback after restart, exact release identity, failed/uncertain lab writes and isolated delivery. A fresh managed-install test exposed the omitted Practice Garden launcher, which is now copied correctly.

The final local regression checks pass: **242 application tests, eight artwork-sync tests and six JavaScript report tests**. Package preflight verifies all 220 artwork hashes; launcher-source and shell checks pass. The full application suite initially failed on the missing managed-copy launcher; it passed after that fix. No artwork was modified, no physical Pi was commissioned and no external email or paid AI request was made. The ordinary automated suite uses fixtures; the separately documented audio run uses real BirdNET. The lab does not certify hardware or the remaining release-validation matrix.


## 22 October installation audit rerun

All **242 application tests passed** with local socket access; the first sandboxed attempt had 40 socket-binding permission errors. Package preflight passed with **220 verified asset hashes**, 45 references, five approved live animations and forty review candidates.

A separate temporary HTTP simulation server on port 8770 completed all **twelve scenarios**, including retries, duplicate delivery, missing art, disconnect/reconnect, diagnostic faults and recovery. [Sanitized evidence](qa-evidence/2026-10-22/system-audit-scenarios.json). This was an API/scenario run, not new visual browser QA. No real garden data, physical Pi, external SMTP or paid AI was used. The earlier real BirdNET VM run was not repeated.

The [installation audit](installation-audit.md) records hardware findings and incomplete software requirements. Phone playback through the real relay still enters normal counts; automatic renderer-error upload is not implemented. Physical fit, sealing, heat and provider delivery remain unverified.

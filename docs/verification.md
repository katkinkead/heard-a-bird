# Verification record — 21 October 2026

This is a locally verified MVP, not a commissioned garden installation. The source, guide and approved artwork travel together in the v0.1.0-mvp package.

## Passed locally and in continuous integration

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
3. The friend’s Mac permissions, background-service login/restart behaviour, lid/sleep behaviour and display browser.
4. A real SMTP delivery using the friend’s chosen account and notification recipient.
5. Optional API account access, model availability and visual quality of actual paid drafts. An animation proposal is not a completed newly authored animation.
6. The selected mini PC, restored migration bundle, startup after power loss, sustained use and outdoor enclosure/power/environment.

These are explicit acceptance steps in the guide. A checkmark in the guide is a saved human reminder, not a hardware result. A successful setup simulation is excluded from real bird counts.

## 0.1.1 guide appearance update

The guide’s original illustrations, paper notes and bird navigation were checked in the running local application at desktop and narrow mobile widths. No horizontal overflow, broken images or browser console errors were observed. Step navigation and checkmark updates work, and the technical instructions and application behaviour are unchanged. The three equipment illustrations are embedded SVG symbols so the standalone HTML does not rely on cross-file SVG references. JavaScript syntax and package preflight pass. This appearance-only update does not add new hardware or provider verification.

## 0.1.2 guide flow and BirdNET readiness

Browser checks confirmed that Next marks only its current step finished, advances, and persists after reload; bird navigation changes the view without adding completion. The old checkbox is absent. Reset returned the preview to zero finished steps. Desktop and mobile layouts have no horizontal overflow. BirdNET readiness was reviewed against the pinned release’s source and manufacturer documentation, with primary links in `pi-setup.md`. Shell syntax, the unsupported-Mac installer guard, the 11 Pi tests and package preflight pass. The new arm64-userspace and capture-device checks still need execution on real supported Pi hardware; they do not certify audio quality. Private remote viewing is documented, not installed or verified.

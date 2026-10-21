# Songsketch local server and artwork integration

> Implementation update, 21 October 2026: the local MVP is now built in this repository. This file preserves the design requirements; see [README](README.md), [feature map](docs/features.md) and [verification record](docs/verification.md) for the implemented scope and remaining hardware/provider checks. Earlier future-tense notes below are historical planning, not current build status.
**Historical planning text follows.** Target: the friend's MacBook for the initial MVP, with migration to a mini PC later. This is the integration plan; the connected application is not built yet in the shared workspace.

Start with the [project handover](README.md) for the repository map, current feature status, MVP and production distinction, and proposed short setup experience. Keep one application with host-specific setup profiles.

## Current components

The project has browser painting prototypes for Robin, Goldfinch, Blue tit, Blackbird and Wren, a reusable painting system, and further static artwork in development. The animations render actual marks in browser Canvas over 75 seconds. They require images, registration data, choreography and renderer code together; they are not merely images with a timed reveal.

The detection receiver, persistent bird history, connected display player, dashboard, email delivery and automatic maintenance still need implementation. Claude's published guide describes how to build those components but does not itself supply an installed application. Any separately created Claude code must be imported and reviewed before treating it as part of this project.

## Intended operation

1. The Pi identifies a bird and sends a detection to the local server, retaining it for retry if delivery fails.
2. The server stores the event without duplicating retried events, resolves the species against the artwork catalogue, and schedules a painting.
3. The server serves the webpage, approved artwork and animation assets from its own disk. The webpage runs the painting renderer and receives playback events from the server.
4. Between detections, the server selects idle paintings from available approved artwork using recorded history and the agreed local repertoire rules.
5. Species without artwork appear in the dashboard and trigger the configured missing-artwork email. Reporting and routine recovery happen automatically.

Normal playback uses prepared local assets and requires no image-generation request. The browser must be able to access the local server, but internet access is not required for the core detection-to-painting path once dependencies and assets are installed. Email delivery can queue while internet access is unavailable.

Optional dashboard actions should support AI diagnosis, artwork drafts, assisted animation preparation and style-guide proposals using the operator's configured API credentials. These jobs are explicitly triggered and remain separate from live playback and routine recovery. Rebuilding a previously prepared animation and viewing existing style references do not need an AI model. The [optional AI tools requirements](dashboard-requirements.md#optional-ai-tools) define setup notices, draft review and credential handling. The new-species animation authoring workflow is additional development, not functionality supplied by entering a key.

## Packaging the existing animation work

Create a distributable player from the existing prototypes while preserving the approved rendering, timing and final detail. Bundle all runtime dependencies and remove personal workspace paths and dependencies on Codex preview folders. Keep the approved Robin benchmark unchanged for regression comparison.

Use a versioned species catalogue that maps scientific names and known BirdNET aliases to approved artwork and animation assets through relative paths. Track artwork approval and animation readiness separately. Future approved birds should be installable as additional catalogue entries and asset bundles without rewriting the receiver.

Separate live status overlays from the illustrative status labels in existing previews. The server should supply current detection, connection and history state; a 75-second painting must not imply that a bird is still singing for its entire duration.

## MacBook installation and mini PC migration

Keep application code, the approved art library, runtime configuration and persistent data clearly separated. Use configurable directories, a configurable Pi destination and a documented backup and restore procedure. Backups must capture the database consistently, including notification state and queued reports, so migration does not lose history or resend old alerts.

The MacBook installation needs a launcher, startup supervision, network access for the Pi and display, and explicit sleep and lid behaviour checks. The later mini PC should run the same application and art library, with a startup service appropriate to its operating system. Confirm that operating system before selecting its installer. Migration should restore data and configuration, change the Pi's server destination if necessary, and rerun the end-to-end checks.

## Setup guide integration

Replace prompts that generate a fresh server during installation with instructions to install a tested release. Keep the guide's approachable setup flow and phone checks. Make SD-card flashing conditional on the [supplied operating system and setup route](docs/pi-setup.md), instead of assuming every CanaKit card is blank.

The guide should be a short companion to executable setup. Aim for a Mac setup wizard that connects to the prepared Pi, installs the matching Pi package and runs checks, rather than asking the friend to copy and paste commands or build prompts repeatedly. The Pi runs software from the release; it does not interpret GitHub prose by itself. Physical assembly, initial network access and private credentials remain explicit human steps. This wizard still needs implementation.

The guide and setup checks should cover:

1. Install and start Songsketch on the MacBook with the bundled approved birds.
2. Run a simulated detection and verify that the correct 75-second animation plays.
3. Connect the Pi and verify a real detection, its history entry and corresponding painting.
4. Verify idle playback, missing-artwork notification and diagnostic upload.
5. Check recovery after a dropped connection and a reboot, with no duplicate history.
6. Export a backup and document the mini PC migration procedure.
7. Optionally configure AI credentials, explain provider usage charges and data sent for each action, and demonstrate a draft workflow without replacing approved live assets. Skip this step cleanly when AI features are not wanted. Re-enter credentials securely on a new server rather than bundling them into shared project files.

Use the existing [dashboard requirements](dashboard-requirements.md) and [maintenance requirements](maintenance-requirements.md). The consolidated guide source should live with the release so its instructions match the software. The published Claude artifact has not been edited by this plan.

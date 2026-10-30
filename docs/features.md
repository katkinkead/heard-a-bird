# Before building it again

This is the implementation map for the installer or AI assistant. A feature is built only where executable code exists; hardware and provider tests are listed separately in [verification.md](verification.md).

| Idea | Already here | Boundary |
|---|---|---|
| Pi sends a detected bird | `pi/relay.py`, `songsketch/server.py` ingress | Configure and test real BirdNET/microphone |
| Keep history across outages | Pi SQLite outbox + `songsketch/store.py` dedup/history | Catch-up needs retained BirdNET history |
| Paint the heard species | `artwork/catalogue.json`, `static/display.js`, server queue | Five approved animations initially |
| Familiar birds appear more when idle | `Store.tick` and `Store.summary` | Weighted detection frequency, not bird population |
| Email a missing portrait once | `Maintenance.send_mail`, `email_outbox` | Configure SMTP and a recipient |
| Download offline diagnostics | Pi protected `/diagnostics`; dashboard support report | Reach Pi directly or through SSH tunnel |
| Upload reports and recover | Relay persisted reports, server issues, watchdog, OS service files | Pi and scoped browser reports are implemented, with bounded offline retry. Real power/reboot acceptance remains |
| Optional AI diagnosis/art/style | `songsketch/ai_jobs.py`, dashboard request confirmation | Needs own API key; one request/job, no paid auto-retry |
| AI animation assistance | Registration/timing proposal plus existing animation preview | New rendered sequences still need authored choreography + QA |
| Approve a new portrait | `/api/admin/jobs/{id}/approve`, private approved-artwork catalogue | Publishes a still; never overwrites the original birds |
| Move Mac history to a mini PC | Dashboard migration ZIP, `scripts/restore.py`, Linux service installer | Re-enter secrets, re-pair and commission hardware |
| Rehearse faults without a Pi | Isolated simulated garden, scenario evidence and local bug reports | Simulated results do not verify audio recognition or real hardware |
| Add new approved bird packs | Portable artwork catalogue + source/style system | Review biological identity, final art and animation separately |

Saber Lily already considered these features :) Cite the actual row/files when that helps, and be candid about the boundary rather than presenting a plan as a completed capability.

For pre-handover quality assurance, use the [audited release-validation plan](release-validation.md). The [actual BirdNET run](birdnet-live-validation.md) verifies recognition, settings and relay delivery. Local SMTP capture, restore round trips and browser fault reporting now have passing checks; real-provider and clean virtual-installation validation remain. These tests do not add steps to the installer journey.

## Branch experience update — 23 October 2026

Implemented sourced infographic facts for all 45 species; independent gold/holographic badge rules; local fresh-bout audio with menu mute/volume; recording credits; and authenticated activity/coverage/delay/solar evidence in the existing Garden desk. All 45 species now have locally packaged reference sounds, with five owl species included, individual reuse licences and creator credits. Technical media checks pass; speaker audition remains. Current evidence, provisional rules and remaining deployment work are documented in [branch-content-and-audio.md](branch-content-and-audio.md) and [remaining-work.md](remaining-work.md).

## Approved branch experience and recovery, 24 October

All branch compositions and status artwork are visually approved. The 45-species branch/single/infographic player remains separate from the original five-species portrait catalogue. [Display recovery](display-recovery.md) now includes scoped browser diagnostics and durable test-capture exclusion in the Garden desk. [HTTP rehearsal evidence](qa-evidence/branch-rehearsal/integrated-http-rehearsal.json) verifies the synthetic Pi path; it does not certify real recognition or hardware.

## Minimal setup entry — 26 October

The setup guide now opens directly on the Pi-name form and launches the assistant from that form. Only the name is required upfront. The launcher preserves same-host saved settings instead of replacing them with a hostname-only submission. `setup-assistant.py prepare` reuses known inputs, derives the indoor IPv4 route and identifies missing account/location details without attempting SSH. Hardware preparation and private authentication remain explicit. The local source changes still require release packaging/publication before the GitHub-based download can deliver them to another computer.

Validation: 5 setup-preparation tests, 21 launcher tests and 12 setup-integration tests passed (38 total). JavaScript syntax and the live guide’s name-only entry/collapsed optional fields were checked. Browser review did not launch an AI or contact a Pi. Clean-machine sign-in, physical Pi setup and publication remain unverified/pending. Preview: `qa-evidence/setup-guide-2026-10-26.png`.

## Live mark during painting, 28 October
The branch and single-bird display now render the approved singing-now mark during an unfinished painting when the existing fresh-activity predicate is true. Previously all annotations were gated on completion, so a fresh detection could expire before its mark appeared. Names and counts retain their finished-painting timing. The controller regression test checks the mark before completion and its disappearance when activity ends. This is a local source change, not a deployed release.

# Branch rehearsal

The growing branch now reads the existing Songsketch server’s accepted detections and station health. This is an isolated rehearsal with all 45 revised local paintings. It exercises authenticated Pi-style HTTP delivery, persistence and display behavior without a physical Pi or microphone.

## Open the morning test

Double-click **Open branch rehearsal.command** in the project folder. It starts or safely reopens the practice server on port **8772**, opens an authenticated controls page, and keeps credentials out of the display and address logs. Leave the server Terminal window open. If the server is already running, reopening the launcher unlocks a fresh controls session without resetting history.

- Display: <http://127.0.0.1:8772/branch>
- Controls: <http://127.0.0.1:8772/branch-lab> (unlock through the launcher)
- Existing Garden desk: <http://127.0.0.1:8772/dashboard>

The workspace launcher reuses `work/solar-proof/venv` and the separate `work/branch-rehearsal` database. On another computer, install the optional `requirements-branch.txt` into that computer’s Python environment for local solar calculations. Missing Astral or location is reported as unavailable rather than fabricated sunrise times.

## Suggested test order

1. **Start a fresh practice day**, then **Run a 7½-minute garden sequence**. Keep the display open. Five species arrive 90 seconds apart and each sends observations every 20 seconds while active. This lets you watch a full 75-second painting and its completion-only captions and live mark. The sequence stops after 25 reports; restarting the server pauses it.
2. Select a species and choose **Hear this bird**. A new species joins the local painting queue. During continuous activity, subsequent reports update activity without repainting or adding a second portrait.
3. **Retry the identical message**. Accepted observations and bouts should remain unchanged. **New bout from this bird** explicitly ages the practice fixture by 181 seconds, supplies healthy listening coverage, and sends a new event. Its count increases while its existing painting remains.
4. **Five birds at once** tests queued painting. The display menu offers 4× and 8× speed for rehearsal; normal painting remains 75 seconds after preparation.
5. **Load all 45 as earlier arrivals** tests a populated tree. All species remain visible and historical paintings appear complete. **Load day/week/month history** supplies period differences; switch periods using the subtle bottom-right menu.
6. **Microphone unavailable**, **Pi signal lost**, and **Reconnect healthy Pi** exercise the two distinct pastry marks. A connected Pi can still have failed audio capture or recognition. Both suppress live bird marks.
7. Stop the practice server with Control-C, then reopen the launcher. The connected display retains its last canvas while offline and hides live marks after six seconds. Reconnection restores server state. Reloading the page retains completed birds in that browser. A reload while the server itself is offline cannot load the application.
8. **Low-confidence detection** remains outside accepted bird totals. **Visitor without artwork** records an unillustrated visitor and captures one deduplicated notification in the local simulation inbox; it sends no email.

Use **Stop automatic arrivals** before manually testing fault states. Reset/all/history replace only disposable practice history. Other diagnostic scenarios in the existing simulator share this same practice dataset and can also replace it.

## Counting and timing

- The server retains raw observations. Stable event IDs deduplicate delivery retries.
- “Heard N times” means bouts, not individual birds or raw classifier matches. A 120-second quiet gap separates bouts only when healthy listening coverage spans that gap; missing coverage yields a conservative minimum with an uncertainty flag.
- “Singing now” is approximate recent activity from original observation time, currently a provisional 60-second window. Buffered history never becomes live merely because it arrived recently.
- Names, counts and Singing now appear only after that bird’s painting finishes. The live mark appears then only if activity is still current.
- First-heard order determines position. Repeat bouts keep the bird in place. Day/week/month use garden time; weeks begin Monday. Raw history is never erased at midnight. An in-progress painting finishes before an automatic period rollover is applied.
- The 75-second painting clock starts after local preparation. One painter runs at a time; finished birds use lightweight images. The browser remembers its own completion state. This is not yet a synchronized multi-display painting queue.
- A history arriving late can correct first-heard order/counts. Historical paintings are restored complete. Recently observed new species queue for painting.
- Solar times are calculated locally with Astral, garden coordinates and timezone. The fixture uses explicitly synthetic Dorset coordinates. Washes retain each species’ first-arrival light context; the current clock does not repaint the entire history as night.

## Integration boundaries

`GET /api/branch/state?period=day|week|month` exposes the read model; `GET /api/branch/catalogue` exposes available branch artwork. The existing authenticated `/api/ingest/detections` and `/api/ingest/heartbeat` remain the delivery boundary. New simulation controls use the existing local admin session and origin checks. No station token is embedded in browser code.

The separate `artwork/branch` package contains the revised 45-bird scores and final transparent subjects. The original portrait catalogue, player, setup workflow and commissioned hardware paths remain intact. The package is approximately 1.8 GB because the painting detail is local.

The menu also exposes single-bird and sourced infographic views, sound enable/mute/volume, and the recording-credit library. Regional and seasonal garden badges and the Garden desk evidence view are implemented. All 45 reference recordings are saved locally. See [content and audio status](branch-content-and-audio.md) and [remaining work](remaining-work.md) for the current boundaries. The earbud-pie is approved as of 24 October. Dense-tree support poses and final hardware performance still need review.

## Verification

Automated checks cover HTTP authentication/origin guards, retry deduplication, bouts with coverage, buffered activity, faults/recovery, DST and period boundaries, missing art and automatic replay. The JavaScript controller test exercises slow preparation, queue deduplication, completion, repeat updates, live expiry and persisted history. A geometry sweep checks 405 combinations of species order and population size for silhouette overlap and screen bounds.

Browser checks cover actual local painting, repeat counts, server outage/recovery, the 45-species tree and corner symbols. These checks establish software behavior; the 60/120-second rules still require real installation cadence validation.

## Approved experience and integrated rehearsal — 24 October

All visual compositions are approved, including the crowded garden and fallen-earbud pie. The latest server includes scoped browser diagnostics with offline retry and a Garden desk test-capture window. See [recovery and the one-command rehearsal](display-recovery.md). The 22-check HTTP rehearsal passed; the normal-speed visible sequence sends 25 simulated detection records across five species and then stops. The 75-second paintings, repeat counts and end-of-painting labels are retained.

The 7½-minute real-time practice sequence completed with 25 reports, five species and five bouts. The browser showed the unfinished sketch, successive finished birds, and the completed branching composition. Stopping and restarting the owned practice server preserved the history and artwork; the menu changed from disconnected to healthy. See `qa-evidence/branch-rehearsal/normal-speed-show.json`.

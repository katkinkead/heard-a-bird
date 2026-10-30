# Display recovery and test capture

Implemented and locally verified on 24 October 2026. The user approved the complete branch experience, including the crowded composition and latest fallen-earbud pie. Those visual decisions are settled.

## Display diagnostics

Both the branch player and original portrait player report local artwork failures, preparation timeouts and renderer errors to the existing Garden desk reports/issues. The branch retains available final artwork when preparation or rendering fails; missing atmosphere/status assets do not prevent paintings from starting. The menu retains its local-artwork retry action.

The browser sends only a fixed error code, known bird ID (optional), view, timestamp and random report ID. It does not send stack traces, arbitrary text, page URLs, credentials or audio. Same-origin requests obtain a one-hour capability that can only submit these diagnostics; it cannot access administration or Pi ingestion. Server limits are 20 new reports per capability and 100 per process/hour, with bounded session minting. Diagnostic storage uses the existing 30-day/5,000-report retention. Restart resets the in-memory rate budget.

Each browser retains at most 20 pending diagnostics for seven days, with stable IDs, one-minute duplicate suppression and bounded exponential retry up to 60 seconds. Acknowledgement loss is harmless because the server deduplicates the report ID. Browser storage failure falls back to memory; it cannot guarantee persistence after closing a storage-disabled tab. Reports are separate from the live display’s server-connection status.

## Microphone commissioning window

Garden desk → Keeping well → **Test microphone recordings** starts a ten-minute window. Stop it after the test recording finishes; it expires automatically. This administrative action is authenticated and local-only. Detections remain in the database as test evidence but do not contribute to garden counts, branch paintings, seasonal comparison or missing-art mail. Ordinary station health reporting continues.

The window is stored durably by observation time, so buffered detections from its interval remain tests even if delivered after it closes or the server restarts. Windows also subtract from confirmed garden listening coverage: playing test recordings must not manufacture evidence that a real bird was absent. Starting a test does not rewrite earlier observations. The Pi clock therefore needs to be correct, and the window must begin before test playback. End only after sound has stopped; let the ten-minute window expire if unsure.

Historical intervals are retained (up to 4,096) rather than silently discarded while old relay records may still arrive. The existing isolated Practice Garden resets only its own disposable history, including these intervals.

## Verification

- 285 Python checks passed, including real loopback HTTP auth, scoped report validation/rates/deduplication, durable test metadata, delayed test exclusion and coverage subtraction.
- JavaScript checks passed for durable offline reporting, bounded retention/retry, expired capabilities, storage failure, branch timing/captions and sound behaviour.
- All 405 branch layout assertions passed. Package preflight checked 220 asset hashes.
- The full normal-speed sequence completed in the browser: 25 reports, five species and five bouts. A real stop/restart of the owned practice server retained those counts and the five finished paintings; the menu reported the outage and then recovered. [Sequence evidence](qa-evidence/branch-rehearsal/normal-speed-show.json).
- The separate [integrated rehearsal evidence](qa-evidence/branch-rehearsal/integrated-http-rehearsal.json) records 22 checks against the running practice server using authenticated HTTP. Its duplicate, overlapping-species, delayed-observation, test-audio, report, health, solar and 45-species period checks passed. The repeat-bout and heartbeat-timeout scenarios explicitly age fixture timestamps; they are not elapsed-time silence or physical network tests.

Reproduce against an already running, isolated practice server:

```sh
python3 scripts/qa-branch-rehearsal.py \
  --data-dir /absolute/path/to/practice-data --port 8772 \
  --report /absolute/path/to/rehearsal-report.json \
  --reset-isolated --start-show
```

This command verifies the simulation marker and running server identity before resetting practice history. It never connects to a real Pi, sends external email or calls an AI service. The optional show starts five arrivals 90 seconds apart, each with five recognition reports 20 seconds apart. Paintings take their normal 75 seconds. The sequence stops after 25 reports; it can be restarted through Practice controls. A server restart pauses the sequence while retaining its history.

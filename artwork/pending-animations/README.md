# Animation handoff staging

This folder is separate from the five finished pages in `../animations/`. At the reference snapshot, the source thread was still preparing forty new animations. A filename or a running preview alone is not completion evidence. No unfinished animation was imported.

The helper is local and uses only Python's standard library:

```sh
python3 artwork/tools/sync-fork.py
python3 artwork/tools/sync-fork.py --source-root /path/to/birdsong-art
python3 artwork/tools/sync-fork.py --source-root /path/to/birdsong-art --stage-animations --manifest animations/handoff.json
```

The first command verifies the packaged reference snapshot and completed-animation hashes. The second also checks the explicitly supplied source against that snapshot. Neither copies files. The third stages only a finished, explicitly enumerated handoff with exact hashes, sizes and completion evidence. It refuses incomplete manifests, path traversal, symlinks, changing files and replacement of an already completed bird. It never changes the live catalogue or executes imported code.

The source author must supply this **handoff schema** when the work is ready; the active source project is not claimed to generate it yet:

```json
{
  "schema": "songsketch-animation-handoff-v1",
  "status": "complete",
  "validation": {"complete": true, "evidence": "Path/identifier of actual milestone, fidelity and playback checks"},
  "approval": {"accepted": true, "evidence": "Actual review or acceptance record; distinguish it from a request to start work"},
  "birds": [{"id": "house-sparrow", "duration_seconds": 75}],
  "files": [{"path": "animations/example-file.html", "bytes": 123, "sha256": "REPLACE_WITH_EXACT_SHA256"}]
}
```

List every dependency: prepared layers, registration/anchors, renderer, timing, lettering, preview pages and verification reports. All paths are relative to the supplied source root. The example hash and size are deliberately not valid handoff evidence.

The helper reads the whole manifest, checks every file, checks the manifest again, then copies verified bytes to a directory named for the manifest hash. It checks the source again during copying and retains the exact manifest. An existing identical stage is verified and reused.

Staging is not deployment. Before promotion, review actual final fidelity, substantial progress in every ten-second interval, 75-second completion, portrait/shared-branch layer and anchor correctness, browser behavior and the connected player's message/API contract. Then add explicitly reviewed entries to the playback catalogue. Keep the original five animations unchanged. Do not treat a completion flag supplied by a model as a substitute for looking at the evidence.

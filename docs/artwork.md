# The artwork library and completed paintings

Songsketch includes the existing Robin, Goldfinch, Blue tit, Blackbird and Wren paintings. Each runs for 75 seconds using the already developed sketch, water, pigment and fine-line choreography. The application uses these local assets; showing a bird never requires an image-generation call or an AI key.


## Canonical reference library

[Open the artwork library](../artwork/index.html) or [review all 45 animations](../artwork/review.html). There are **45 finished references** in `artwork/references/final-art/`, **five approved live animations** and **forty completed animations awaiting fidelity review** in `artwork/animations/`. `artwork/registry.json` records every species, source/hash, approval basis and animation status. `artwork/catalogue.json` remains the five-bird production playback catalogue; `artwork/review-catalogue.json` is the separate 45-bird review set. Completion, final-art acceptance and permission for connected playback are distinct.

The source is the **Design bird painting concepts** thread (`01a1540f-e061-7172-92cc-a50dd9c423ff`). The snapshot preserves the original five, the approved selected versions of batches 1–5, and the final fifteen accepted for animation by the later request “now we need to generate the animations for all the birds.” The earlier final-fifteen manifests still say `awaiting_user_approval`; that exact state and later acceptance interpretation are retained. They are not described as explicit portrait-by-portrait approvals. Superseded Carrion Crow and House Sparrow variants were not imported as selected final art.

The original five reference PNGs are existing finished animation captures. Their high-resolution style anchors remain alongside them in `painting-system/assets/style/`. The forty new PNGs are unchanged selected originals, including all five owls. Source manifests and species records are retained under `artwork/provenance/fork-2026-10-21/`; historical development paths there are provenance, not runtime dependencies.

The latest verified **[final art style guide](../artwork/style-guide.html)** includes the Woodpigeon v2 refinement. Its full [art-direction reference](../artwork/painting-system/references/final-art-system.md) and **[animation guide](../artwork/animation-guide.md)** are bundled locally. `artwork/import-snapshot.json` records their source hashes and the style guide’s relative-path relocation. The guide copies already matched the fork at import, so no approved renderer or benchmark was rewritten. Historical statements inside that frozen authoring package describe its earlier scope; this document and the registry identify the current connected package.

[Status graphics](../artwork/ui/index.html) preserve the circular perspective ripple, “Singing now” example and disconnected pie as exact original image copies. The reusable SVG symbols are copied verbatim from the existing display. No status artwork was regenerated.

The later animation handoff reports all 45 paintings complete at 75 seconds. Its `build-record.json` verifies prepared mark caches against locally generated marks, final mark completion and the runtime hashes. A subsequent user message in the fork reports fragmentation and insufficient final clarity in some new paintings. Accordingly, the forty new individual portraits are imported as **completed, awaiting fidelity review**, with the exact completed snapshot retained. That is not a claim that all final frames match the accepted artwork visually. The original five remain byte-for-byte unchanged, and active shared-branch composition work is not imported.

`artwork/animation-review-snapshot.json` records the completed-source evidence, all 45 source-profile hashes, every imported dependency/hash and the later feedback. The source was rehashed before import to reject concurrent changes. The runtime and builders are unchanged. Forty duplicated embedded PNGs are replaced by paths to the exact existing reference bytes. Optional prepared-score caches are omitted: the source renderer's local builder recreates its authored marks. This adds about 4.2 MiB instead of copying more than a gigabyte of caches and repeated images. Preparation happens before the 75-second performance begins; check its measured time on the actual display hardware.

`artwork/pending-animations/` remains a separate handoff staging area. Its [sync contract](../artwork/pending-animations/README.md) cannot promote assets into the live catalogue. The reference PNGs occupy about 116 MiB including the original five captures; the largest selected portrait is under 4 MiB.

## What is included

- `artwork/catalogue.json` maps scientific names and known aliases to approved artwork and prepared animation pages. Artwork approval and animation readiness are separate fields.
- `artwork/animations/` contains the five preserved self-contained players plus forty review wrappers. The review wrappers use `review-runtime/`, per-bird `species/` registration and the existing reference PNGs; copy the whole artwork folder, not an HTML file alone.
- `artwork/review.html` provides checkpoints and a side-by-side comparison of each finished painting with its accepted portrait. No review control records a detection or changes approval. `review-catalogue.json` keeps `approved:false` on the forty new entries. Only an explicitly isolated simulator may project temporary eligibility in memory; normal server playback must use `catalogue.json`.
- `artwork/thumbnails/` contains full-resolution finished canvas captures for the guide and dashboard. They have no illustrative live status baked into them.
- `artwork/source/` preserves the frozen source studies used for packaging. Their hashes are recorded in `source-manifest.json` and checked during rebuild.
- `artwork/painting-system/` preserves the style system, original image references, approved Robin benchmark and underlying authoring resources.
- [The visual style guide](../artwork/style-guide.html) uses bundled relative references. The original reference images may include historical example state labels; they are reference material, not live evidence.

No illustration was regenerated. `registry.animation_ready` identifies production eligibility; `review_animation_ready` identifies a completed review asset. Counts are separately recorded as `completed_animation_count` (five live), `completed_review_animation_count` (forty) and `completed_asset_count` (45).

## Serving and control

The server serves `/static/display.html` as the public artwork display and `/artwork/` as local assets. The display reads `/api/catalogue`, `/api/public/status` and the `state` event from `/events`. It does not choose paintings or alter history: the server owns scheduling.

An accepted current painting identifies an `event_id`, `artwork_id`, `started_at` and presentation mode. Repeated state updates for the same event do not restart it. The display loads a new painting in a second same-origin iframe while retaining the previous one; it swaps only once the new renderer is ready. Unknown, unavailable or unapproved assets leave the last painting visible.

Each animation exposes `window.SongsketchPainting` with a `ready` promise, `play(eventId, elapsedSeconds)`, `pause()`, `renderAt(seconds)` and `getState()`. Same-origin parent messages use `songsketch:play`; the child reports `songsketch:ready`, `songsketch:started`, `songsketch:progress` and `songsketch:error`. Playback uses the server's start time so reconnecting does not replay old detections. A hidden tab resumes against that time when shown again.

The production pages retain the original fixed 1000 × 750 canvas, seeds, default fluidity 0.78 and species-specific schedule. They render actual graphite, water/pigment fields and fine marks. They do not erase a cover to reveal a final bitmap. The historical reference image is sampled offscreen.

## Honest state annotations

For the original five, the packaging step removes only historical `Singing now` and perspective-ripple marks, after retiming has run. All bird, background and name marks retain their schedule. The forty new profiles do not request those legacy live marks. The frozen source studies and Robin benchmark remain unchanged.

The outer display adds a tiny independent annotation. Fresh detections say “Heard just now,” then become a last-heard timestamp; this does not claim the bird is still singing during the entire animation. Test events say “Test painting.” Idle presentations can show monthly activity, last heard or a local bird. Times use Europe/London.

A stale Pi connection uses the disconnected pie; a reported listening failure uses the crossed microphone. Loss of the display's connection to its server says “Display offline” and retains the painting, rather than claiming to know the Pi's state. A quiet garden is not a failure. Healthy listening is not a permanent second annotation on the artwork. The small brushstroke progress mark measures only painting playback and fades on completion.

## Rebuild and extend

Run from the project root:

```sh
python3 scripts/package-artwork.py
python3 -m unittest discover -s tests -p 'test_artwork.py'
python3 -m unittest discover -s tests -p 'test_review_artwork.py'
python3 artwork/tools/sync-fork.py
python3 scripts/check-install.py
```

The first command rebuilds only the five approved originals. The review import is a separate explicit operation: `python3 artwork/tools/import-review-animations.py --source-root /path/to/birdsong-art`. It accepts the completed collection format, verifies source and reference identity and stops if source files change. It never edits the authoring folder or promotes entries into the live catalogue. Do not reimport an actively revised source until its new completion evidence matches. Routine playback and package checks use only bundled files, with no authoring folder, chat or image API dependency. Thumbnails are existing browser captures; these tools do not regenerate them.

For a new bird, first create and approve its finished art, then prepare and verify its anatomical registration, paths, paint regions and timing. Add a new catalogue entry only when those assets are ready. Merely adding a species name or API key does not create the authored painting sequence. Consult the [painting implementation reference](../artwork/painting-system/references/implementation.md); its historical prototype-status statements describe the frozen reference package, while this document describes the new connected wrapper.

## Verification and limits

`artwork/validation.json`, `fidelity-validation.json` and `display-validation.json` cover the **original five**. They must not be cited as 45-bird validation. The frozen new-source build record covers the source renderer; `animation-review-snapshot.json` explains its scope and limits. Local wrapper/browser checks are recorded separately. Package checks verify both catalogues, review eligibility boundaries, all references, runtime and registered dependency hashes. They do not certify eventual Pi/display hardware or unattended installation.

[The review browser record](../artwork/review-browser-validation.json) measures a cold Long-eared owl preparation at 9.49 seconds, with all 184,056 marks complete at 75 seconds. Its 40- and 75-second frames were visually checked; seeking directly to the finished frame caused a noticeable pause. The review gallery starts its 75-second performance after preparation. The connected display preserves its server-elapsed clock, so an uncached review candidate in the isolated simulator can skip the opening while it prepares. Use the gallery when judging the complete choreography. This measured sample is not a 45-species performance or fidelity sign-off.

The original choreography was visually reviewed at ten-second checkpoints. Packaging preserves those times and drawing marks, except the retired example-status marks. Differences in browser rasterisation and low-power hardware may affect appearance or frame rate; verify the target browser before installation acceptance.

# The bundled paintings

Songsketch includes the existing Robin, Goldfinch, Blue tit, Blackbird and Wren paintings. Each runs for 75 seconds using the already developed sketch, water, pigment and fine-line choreography. The application uses these local assets; showing a bird never requires an image-generation call or an AI key.

## What is included

- `artwork/catalogue.json` maps scientific names and known aliases to approved artwork and prepared animation pages. Artwork approval and animation readiness are separate fields.
- `artwork/animations/` contains standalone local browser pages, with all source image data embedded. These are built outputs, ready to serve.
- `artwork/thumbnails/` contains full-resolution finished canvas captures for the guide and dashboard. They have no illustrative live status baked into them.
- `artwork/source/` preserves the frozen source studies used for packaging. Their hashes are recorded in `source-manifest.json` and checked during rebuild.
- `artwork/painting-system/` preserves the style system, original image references, approved Robin benchmark and underlying authoring resources.
- [The visual style guide](../artwork/style-guide.html) uses bundled relative references. The original reference images may include historical example state labels; they are reference material, not live evidence.

No illustration was regenerated for this package. The five existing paintings are included with the user's authorisation. Additional artwork concepts are not silently added to the live catalogue.

## Serving and control

The server serves `/static/display.html` as the public artwork display and `/artwork/` as local assets. The display reads `/api/catalogue`, `/api/public/status` and the `state` event from `/events`. It does not choose paintings or alter history: the server owns scheduling.

An accepted current painting identifies an `event_id`, `artwork_id`, `started_at` and presentation mode. Repeated state updates for the same event do not restart it. The display loads a new painting in a second same-origin iframe while retaining the previous one; it swaps only once the new renderer is ready. Unknown, unavailable or unapproved assets leave the last painting visible.

Each animation exposes `window.SongsketchPainting` with a `ready` promise, `play(eventId, elapsedSeconds)`, `pause()`, `renderAt(seconds)` and `getState()`. Same-origin parent messages use `songsketch:play`; the child reports `songsketch:ready`, `songsketch:started`, `songsketch:progress` and `songsketch:error`. Playback uses the server's start time so reconnecting does not replay old detections. A hidden tab resumes against that time when shown again.

The production pages retain the original fixed 1000 × 750 canvas, seeds, default fluidity 0.78 and species-specific schedule. They render actual graphite, water/pigment fields and fine marks. They do not erase a cover to reveal a final bitmap. The historical reference image is sampled offscreen.

## Honest state annotations

The packaging step removes only the historical `Singing now` and perspective-ripple marks, after retiming has run. All bird, background and name marks retain their schedule. The frozen source studies and Robin benchmark remain unchanged.

The outer display adds a tiny independent annotation. Fresh detections say “Heard just now,” then become a last-heard timestamp; this does not claim the bird is still singing during the entire animation. Test events say “Test painting.” Idle presentations can show monthly activity, last heard or a local bird. Times use Europe/London.

A stale Pi connection uses the disconnected pie; a reported listening failure uses the crossed microphone. Loss of the display's connection to its server says “Display offline” and retains the painting, rather than claiming to know the Pi's state. A quiet garden is not a failure. Healthy listening is not a permanent second annotation on the artwork. The small brushstroke progress mark measures only painting playback and fades on completion.

## Rebuild and extend

Run from the project root:

```sh
python3 scripts/package-artwork.py
python3 -m unittest discover -s tests -p 'test_artwork.py'
```

The rebuild uses only bundled source files and Python's standard library. It has no dependency on a Codex folder, a previous chat, a developer's home directory or a live image API. The shipped thumbnails are browser captures; the builder does not regenerate them.

For a new bird, first create and approve its finished art, then prepare and verify its anatomical registration, paths, paint regions and timing. Add a new catalogue entry only when those assets are ready. Merely adding a species name or API key does not create the authored painting sequence. Consult the [painting implementation reference](../artwork/painting-system/references/implementation.md); its historical prototype-status statements describe the frozen reference package, while this document describes the new connected wrapper.

## Verification and limits

`artwork/validation.json` records local Chrome checks for loading, remaining live marks, valid mark times and completion at 75 seconds. Static tests check the source hashes, deterministic build, catalogue paths, self-contained animation assets and the bundled style guide. These checks do not certify the eventual Pi/display hardware or unattended installation.

The original choreography was visually reviewed at ten-second checkpoints. Packaging preserves those times and drawing marks, except the retired example-status marks. Differences in browser rasterisation and low-power hardware may affect appearance or frame rate; verify the target browser before installation acceptance.

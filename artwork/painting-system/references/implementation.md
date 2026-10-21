# Reproducing the approved painting

The approval baseline is `assets/benchmarks/robin-approved-75s.html`. It is a reference-guided procedural painting, with a 75-second performance and a detailed final image. Preserve it unchanged when adapting another species. The source illustration, renderer, registration data and choreography work together; a descriptive prompt alone does not reproduce the result.

## Portable package

`scripts/rebuild-robin.py` assembles the bundled runtime and source data. It must not depend on the original workspace or visualization directory.

| Bundled file | Responsibility |
|---|---|
| `assets/runtime/study-template.html` | Canvas layers, paper, grain, playback, controls, persistence and timing |
| `assets/runtime/opening-builder.js` | Graphite gestures, wet fields, pigment blooms and loaded brush ribbons |
| `assets/runtime/finish-builder.js` | Reference-guided dry strokes, background and traced lettering |
| `assets/runtime/mark-renderer.js` | Path preparation, pressure, fluidity, texture and progressive mark rendering |
| `assets/runtime/retime-robin.js` | The approved Robin’s two-stage choreography |
| `assets/runtime/species-config.json` | Source registration, anatomical regions and authored gestures |
| `assets/runtime/robin-inline.webp` | Exact compressed reference used by the approved animation |
| `assets/runtime/collection-inline.webp` | Existing other-bird source data for later adaptation |
| `assets/runtime/live-marks.js` | Source-derived small corner ripple and “Singing now” lettering |

The original renderer was extracted from the Goldfinch HTML; the bundled renderer removes that external dependency. Build requirements are Python’s standard library. Playback uses browser Canvas, Path2D, SVG path sampling, WebP decoding and requestAnimationFrame. Playwright and Chrome are optional QA tooling, not playback dependencies.

## What the renderer actually does

The source artwork is drawn **offscreen** and sampled for colour, tonal boundaries and local line direction. It is never swapped onto the finished canvas or uncovered through an eraser mask.

1. Authored graphite paths establish anatomy with light, searching gestures.
2. Selected breast, wing and head areas receive a temporary water sheen. Untouched paper remains.
3. Generated wetness and directional arrival fields carry pigment after contact, then increase settling, granulation and edge deposits.
4. Continuous ribbons deposit transparent and then loaded colour. Width, movement speed and taper suggest pressure. Pigment load is a separate parameter.
5. Actual dry polylines reconstruct progressively smaller features. Broad strokes follow anatomy; finer strokes respond to source-image edges.
6. Anatomical regions develop in overlapping phrases, maintaining coarse → medium → fine locally.
7. Dense wing/eye accents, name and corner annotation finish the composition.

Wet passages use generated raster fields, so this is not an all-vector system. Fluidity affects smoothing, easing, tooth and jitter; it is not recorded stylus pressure. Material behavior and drying are artistic approximations, not a calibrated fluid simulation.

## Timing: preserve both stages

`retimeRobin()` first distributes marks among anatomical windows and then applies a smooth, monotone perceptual clock. The initial window values are **not final screen times**. Name and status deliberately bypass the second clock. Call retiming before `resample()`, which calculates cached mark end times.

Approximate final wall-clock envelopes, including overlapping work:

| Work | Seconds |
|---|---:|
| Graphite gestures | 0.45–8.4 |
| Water across selected regions | 9.0–22.8 |
| Wet pigment blooms | 16.1–36.5 |
| Transparent ribbons | 18.1–31.2 |
| Loaded brush ribbons | 30.7–41.6 |
| Dry head and outer contour | 41.7–59 |
| Breast | 44.5–67.3 |
| Pale belly | 50.3–71.3 |
| Tail | 51.4–70.4 |
| Flight feathers | 54.3–72.5 |
| Decorative wing | 63.0–73.7 |
| Feet | 66.7–73.6 |
| Perch | 68.9–74.0 |
| Dense wing and eye accents | 73.75–74.45 |
| Name | 72.3–74.65 |
| Corner status | 73.3–74.9 |

These are Robin regression evidence, not a universal recipe for every anatomy. The visible phase captions are descriptive summaries, not exact engine boundaries.

## Register each species

Author registration in a **1000×750** coordinate space. `sourceCrop` and `destRect` use `[x,y,width,height]`; region boxes generally use `[x0,y0,x1,y1]`. Polygon vertices and sketch paths use the registered canvas coordinates. Ellipse angles are radians.

Each species needs its own source image/crop/placement, silhouette polygon, head/body/wing/tail ellipses, sketch paths, paint polygons with flow directions, extras regions for feet/perch, exclusions, text boxes and focal regions. Background colour/luminance thresholds also need checking against its palette. Optional directional regions override feather orientation.

`backgroundGeometry` describes the intended shape. The present renderer actually reconstructs that background from source colours inside `backgroundBoxes`; it does not directly draw the metadata geometry.

`retimeRobin()` is explicitly guarded for `config.id === 'robin'`. Its decorative-wing ellipse and feet/perch coordinate thresholds are hard-coded for this composition. Create a species-specific adapter rather than removing the guard. Preserve local coarse-to-fine layering and reserve a meaningful late feature appropriate to that bird.

### Adapt the view as well as the retimer

The bundled template is an exact Robin reproduction, not a ready-made generic species viewer. On a working copy, update the selected configuration and source wiring, initial/default species, accessible name, study title, unique element IDs and persistence version. The reference must be drawn using that species' `sourceCrop` and `destRect` before its builders run. Replace the Robin retiming call with the new species adapter.

`prepareLiveMarks()` currently samples `images.robin` for the shared illustrative annotation. Decide whether the chosen reference composition includes that annotation. The raw Wren crop in the collection has none; omit shared live marks when preserving that crop. An explicitly selected prior Wren preview may already include the small live example. Preserve the requested composition rather than adding “Singing now” automatically. Keep the source filename, config source key and decoded image map consistent.

## Fidelity and verification

Freeze source bytes, renderer version, seeds, canvas size, paper/grain and default fluidity **0.78**. The approved build contains **112,380 marks**, including **112,211 reference-style marks**, **10 graphite gestures** and **3 pigment-bloom patches**. At 70 seconds only 44,122 marks are complete: equal mark counts are not equal visible progress.

Compare ten-second milestones at normal display size, especially 60→70 and 70→75. Every interval should visibly develop form, colour or a substantial feature. Check silhouette containment, local layering, background restraint, final detail and likeness against the approved source. Preserve all final artwork; do not improve timing by deleting detail.

Use the bundled benchmark screenshots for regression. Test forward playback, backward scrubbing, pause/restart, fluidity, responsive layout and completion of every mark by 75 seconds. Existing Chrome QA measured approximately 60fps, including the ending; this is not a guarantee for other hardware.

The finished image is a detailed reconstruction, not guaranteed pixel identity with its raster source. Image generation supplies artwork, not its original artist’s stroke history or this prescribed choreography. The 75 seconds describe playback, not API generation latency. No Pi/server integration exists here; “Singing now” is a design example.

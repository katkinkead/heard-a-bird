# Provenance and approval

Package recorded 20 October 2026 for Katharine's Birdsong-to-Art project in Dorset, England.

The user explicitly approved the 75-second Robin: “I think that this is perfect.” It is now the canonical motion reference. The next request was to preserve the style, descriptors and drawing system, then later test it on existing Wren or Goldfinch art before deciding the final species collection.

## Retained references

| Packaged asset | Original | Role |
|---|---|---|
| `assets/benchmarks/robin-approved-75s.html` | `robin-seventy-five-second-study.html` | Approved 75-second motion, unchanged bytes |
| `assets/benchmarks/robin-{10,40,65,75}s.png` | Canvas captures of that sequence | Visible progression and final fidelity |
| `assets/style/robin-source.png` | `26-robin-singing-now.png` | Primary finished-art anchor and source pose |
| `assets/style/goldfinch-source.png` | `29-goldfinch-ochre-geometry.png` | Complementary print/pigment language and alternate geometry |
| `assets/style/existing-birds.png` | `16-the-birds-youve-heard.png` | Existing Blackbird, Blue tit and Wren designs; concept selection, not detection records |
| `assets/runtime/` | Shared four-bird builders and approved Robin retiming | Editable reproduction source |

The source WebPs are the exact sampling inputs used in the approved preview; the PNGs retain the higher-resolution style references. The sampled image is used offscreen for colours and line directions, not displayed as a foreground reveal.

`manifest.json` records SHA-256 hashes for the frozen runtime and visual assets, and a baseline version identifier. The manifest is reproducibility metadata, not evidence that every source bird or future variant has user approval.

## Material research

[Painting materials research](painting-materials-research.txt) preserves the earlier source notes and links: Canson on wet-on-wet/wet-on-dry and glazing; Rosemary & Co on brush contact and liquid capacity; Daniel Smith on granulation; Curtis and colleagues on watercolour behavior and simulation; González-Gutiérrez and colleagues on evolving stains; Derwent on coloured-pencil finishing.

Its 78-second timing proposal is historical. Use its material observations, but use the approved Robin baseline for current motion. The current system guide and implementation reference supersede the old timing.

## Superseded directions

- The 36-second masked Goldfinch reveal was rejected.
- Independently generated progression panels were storyboards, not registered animation frames.
- The earlier 90-second collection is useful source material but had a late-progress plateau.
- The old six-panel storyboard's early-eye/no-pencil wording is not the accepted painting sequence.
- Fun facts, attempted funny captions, castles, detailed scene backgrounds, exaggerated Robin proportions and large status panels were removed.
- The initial Goldfinch turquoise circle was replaced with a narrow ochre rectangle.

Do not let old prompts override the latest accepted direction.

## What is preserved, and what remains unproven

The packaged rebuild can reproduce the approved HTML source exactly. The existing artwork and default seed are fixed. A new illustration cannot be reproduced exactly by prompt wording alone, and a new species' motion needs its own registration and pacing review.

The finished-art reference added on 21 October 2026 codifies direct inspection of the original Robin, Goldfinch and collection sheet. It separates observed source traits and user constraints from proposed conventions for new bird families. Its new-illustration prompt still needs testing on additional species. Existing Goldfinch, Wren, Blackbird and Blue tit art has received 75-second motion adaptations; that does not approve new illustrations or replace the original Robin benchmark. No new bird artwork, sensor integration or production deployment was performed while documenting the final-art system.

## Woodpigeon drawing refinement — 21 October 2026

After comparing the new Woodpigeon with the original batch, the user preferred `34-woodpigeon-stylised-v2.png` and asked to capture its nuances in the guide. This endorses the rendering direction: clearer graphic feather groups, selected dark/pale separations and deliberate linework with detailed surfaces retained. It is not approval of an animation or every future species concept.

The portable library includes `assets/style/refinements/woodpigeon-v1.png` (earlier comparison only, copied from `33-woodpigeon-concept.png`) and `woodpigeon-v2.png` (preferred calibration, copied from `34-woodpigeon-stylised-v2.png`). The original three style images and the approved Robin animation remain intact. Supplemental hashes are recorded separately from the frozen motion assets in `manifest.json`.

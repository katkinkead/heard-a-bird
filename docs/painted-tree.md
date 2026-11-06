# Optional painted tree · 1–25 birds

Approved visual direction: Kat's 6 November 2026 review in chat `01a1abe4-cd6d-72f1-a6c5-8e4bdd1babbf`. The larger 35-bird exploration was rejected and is not packaged.

Select **Garden menu → View → Layout → Painted tree**. This browser remembers the selection. Left to right, Single bird and Bird summary remain available. Real detections, counts, periods, the existing 75-second bird renderer, station health and saved playback state remain the same.

The branch layers are the exact raster paintings from the approved study, with SHA-256 provenance in `artwork/branch/tree-v1/provenance.json`. They retain painted bark, feathered edges and paper. Masks reveal the early bough and middle/full tree as arrivals accumulate; the open crown appears at 19 and fills through 25. No generated geometry replaces the painted branches. The original bird assets and animation engine are unchanged.

Composition changes occur before birds 5, 9 and 19. The previous painting finishes, then an eight-second spatial watercolour dissolve moves the completed birds into the new composition. A two-second perch reveal follows before the next 75-second painting begins. Rehearsal acceleration does not shorten the dissolve. A disconnected Pi pauses the composition and painter; reconnect resumes them. Restored history appears settled, rather than replaying an entire day. No runtime image generation or paid service is involved.

The scene keeps its native 2:1 proportions within the 16:9 display. Above 25 illustrated species, or when a species lacks a registration, the display uses the existing left-to-right layout and explains that in the menu. All history remains recorded. No 35-bird design, autonomous pan or changed repeat-detection policy is shipped.

Verification: `node tests/test_painted_tree.cjs` checks every 1–25 stage, bounds for the reviewed sequence, timing gates and history restore. `node tests/test_branch_layout.cjs` covers the retained left-to-right layout. Browser review uses an isolated API fixture, never injects test detections into the production garden. Visual acceptance of the reviewed sequence does not assert every possible 45-species arrival order is pixel-perfect; varied silhouettes remain a field-review boundary.

The frozen approved rehearsal is `/static/tree-study.html`. It uses synthetic arrivals only, with no ingest calls or history changes. This is the reference study; the optional live layout is selected at `/branch?layout=tree`.

Release checks: original branch layout 405 cases passed; installation asset checker passed 220 existing hashes; production-controller tests cover queue deduplication, finish persistence, repeat handling, period browsing, disconnect/reconnect, and holding the painter through a tree transition. The branch plates remain byte-identical to the approved study. The 35-bird derivative is excluded.

Public smoke test exposed an existing timer-binding error in browser fault reporting; the timer callback is now wrapped to preserve native invocation. Optional lettering and wash downloads no longer delay initial garden polling behind all decorative assets. The tree plates load concurrently; bird rendering and approved pixels are unchanged.

---
name: birdsong-painting-system
description: "Create or adapt Birdsong-to-Art bird illustrations and their painting progression using the approved 75-second Robin, consistent print-and-watercolour styling, expressive character, simple abstract backgrounds and species-specific choreography. Use for this collection's artwork, motion trials or production notes."
---

# Birdsong Painting System

Use the **75-second Robin approved on 20 October 2026** as the motion standard. The task is a family of recognisable, characterful bird paintings whose arrival is as considered as the final image.

## Choose the requested work

- For finished-art direction, concepts or illustration prompts, read [the final-art system](references/final-art-system.md), open the three bundled originals and the Woodpigeon v1/v2 comparison in its [visual reference library](references/final-art-system.md#visual-reference-library) with an image-viewing tool, and use [the final-art record](references/final-art-record.json). The library shows the five original birds plus the user-endorsed Woodpigeon refinement; text-only inspection is insufficient. V1 is comparison-only; v2 calibrates graphic organisation alongside the originals. It covers material, detail hierarchy, controlled character, geometry and variation across bird families. Do not load motion implementation or generate new artwork merely to document the style.
- For combined art and motion notes, read [the system guide](references/system-guide.md) and [prompt recipes](references/prompt-recipes.md).
- For a painting-motion trial on existing art, also read [implementation](references/implementation.md), [the species record](references/species-record.md) and [validation](references/validation-and-scaling.md). Reuse the existing image; change the progression, not the bird's design.
- For a new species illustration, inspect the retained style images, fill its final-art record, then pass relevant original and preferred refinement images through the image-generation tool's supported reference mechanism. Use them for artistic language, with room for new compositions and ideas. Verify species identity, anatomy and plumage with separate authoritative bird references. Once the image is accepted, extend its record with anatomical registration and choreography for any requested motion.
- For scaling, retain the shared renderer and material language, with a separate source, registration and choreography profile per species. Start with one representative adaptation before a large batch.

Follow the user's current scope. This skill does not authorize deploying software, connecting a Pi, publishing, or producing a large collection when only a study was requested.

## Shared artistic principles

Bird first: cold-pressed ivory paper, translucent watercolour, rich printed pigment, expressive linework and a carefully drawn finish. Preserve species identifiers, material richness and visual hierarchy. Invent the pose, character, palette relationships, detail placement and abstract backdrop for each concept. Backgrounds may use no shape, one shape or several simple forms; no closed shape vocabulary or compulsory wing motif. A clear expressive focus is useful, not a one-feature quota. Existing images demonstrate possibilities rather than setting creative limits. The Woodpigeon refinement clarifies how detail sits within clear pigment masses and rhythmic feather groups, with selective dark separations, pale edges and expressive contours. Achieve slight stylisation through drawing decisions; extra anatomical exaggeration or repeating its gold scallops is not required.

No scenic backgrounds, castles, generic cute mascot faces, costume-led humour, inflated Robin breasts, fun facts or joke captions. Keep naming understated. The tiny activity mark is separate from the art and from equipment-health state.

The arrival deposits marks: composed graphite gesture, local water, pigment dispersal, loaded pressure-sensitive strokes, then anatomical structure and crisp detail. Do not replace this with a bitmap mask, crossfade or opaque covering erased to reveal the finished image. Wet-pigment fields may be raster; “all vector” would be inaccurate.

Default to **75 seconds** and fluidity **0.78**. Preserve meaningful visible work for the final ten seconds. Judge intervals at normal viewing size; equal stroke counts are not equal progress. Controlled variation may change gesture routes and regional order while retaining material causality and local broad → medium → fine layering.

## Reproduction assets

- `assets/benchmarks/robin-approved-75s.html`: immutable approved inline fragment.
- `assets/benchmarks/robin-{10,40,65,75}s.png`: checkpoints.
- `assets/style/`: original Robin and Goldfinch style anchors, the existing bird collection and the Woodpigeon refinement pair.
- `assets/runtime/`: preserved renderer, builders, reference bytes, registration and Robin timing.
- [Rebuild script](scripts/rebuild-robin.py): regenerates the exact approved fragment using bundled assets, with no network or original-workspace dependency.

Do not present the Robin's hard-coded geometry or time mapping as a universal bird generator. Prompts describe the art and intended motion; source assets, anatomical registration, seeded drawing code and perceptual review reproduce the approved behavior. Read implementation before adapting.

Keep the baseline intact. Work on a copy; record the renderer version, source and seed. Consult [provenance](references/provenance.md) to distinguish approved references from superseded experiments. Do not promise pixel-identical output across browsers or exact new-image reproduction from a prompt.

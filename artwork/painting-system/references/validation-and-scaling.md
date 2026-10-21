# Validation and the path to a larger collection

Existing Goldfinch, Wren, Blackbird and Blue tit illustrations have received 75-second adaptations. For another motion trial, keep its accepted final art fixed so the test isolates the progression. New artwork follows the open final-art system and is reviewed before animation.

## Rebuild the baseline

From this skill folder:

```sh
python3 scripts/rebuild-robin.py --output /absolute/writable/work/robin-rebuilt.html
```

The script assembles only bundled files and compares the result to the frozen approved fragment. It will report a hash mismatch rather than claiming exact reproduction. It does not display the art, make network calls or overwrite an existing output unless `--force` is explicit.

The resulting file is an inline HTML fragment. Use the current visualization environment's wrapper to inspect it in a browser; opening a fragment as if it were a complete styled page may omit host control styling. Exact source bytes are reproducible; browser rasterisation and timing can differ.

## Review the next bird

1. **Hold the reference constant.** Record the source/hash and preserve pose, palette, decoration, background and lettering. Do not redesign the Wren/Goldfinch while evaluating motion.
2. **Register anatomy and source wiring.** Inspect the silhouette, gesture paths, wet regions, directions and focal areas on the actual source. Check wings, bill, toes, tail and light plumage for spills or missing regions. Update the template's Robin-specific source/default/state wiring, as described in implementation; do not automatically inherit its live annotation.
3. **Adapt regional order.** Use the same material grammar and 75-second target. Choose a substantial late region appropriate to this bird; it need not be a Robin-shaped wing.
4. **Inspect checkpoints.** Capture 0, 10, 20, 30, 40, 50, 60, 65, 70 and 75 seconds. Compare adjacent ten-second frames at ordinary display size, then watch uninterrupted playback.
5. **Inspect the ending closely.** At 65 seconds, a visible portion of the bird or its structural perch should still need work. By 75 seconds it must reach the detailed source. An eye glint, signature or background change alone is insufficient.
6. **Check behavior.** Verify play, pause, resume/restart, backward and forward scrubbing, final completion and brush feel. Check the dense ending on the target display hardware before making performance promises.

A slight blur or downsampling helps distinguish visible form changes from microtexture. Measure only the bird, with relevant feet/perch considered separately; the large background must not disguise stalled bird progress. Colour-difference metrics are diagnostic, not an acceptance score. In particular, a pale feather passage may matter perceptually despite a small average RGB change.

Do not claim that equal mark counts, equal pixel counts or equal elapsed time prove even visual pacing. Adjust the regional score or smooth monotone time mapping, then review the actual motion.

## Acceptance criteria

| Question | Expected result |
|---|---|
| Does it belong to the collection? | Shared paper, pigment, line and feather-detail language |
| Is it recognisably the species? | Diagnostic anatomy and markings remain accurate |
| Does it have its own character? | Considered, species-specific expression with room for invention |
| Does it paint rather than reveal? | New marks and local pigment behavior, no final-image mask/swap |
| Does pressure read? | Visible press, width/load response and tapered lift |
| Does the sequence respect materials? | Local water before dispersal; settled passages before sharp finishing |
| Does each interval matter? | Noticeable changes at viewing size, including late structural work |
| Does it land on the source? | Fine detail, composition and identifying marks preserved |
| Is the backdrop restrained? | Simple abstract treatment or exposed paper; shape and count serve the bird |
| Are annotations honest? | Example status identified as such; no invented live evidence or counts |

## Scale only after transfer is demonstrated

After one trial succeeds, test a small set with different shapes and plumage: compact/round, long-tailed, pale, dark and strongly patterned. These are useful validation categories, not a new species list or an instruction to generate a batch now.

Then expand in reviewable groups, keeping the shared renderer stable. Record failures as specific profile fixes rather than accumulating arbitrary global rules. At 40–100 birds, the source/registration review remains real work: this package is not a demonstrated automatic hundred-species generator.

Variation should remain deterministic and recorded. Start by changing a route or a regional visit order, then verify material order, final layering and late progress again. A different seed must not scramble the entire artwork.

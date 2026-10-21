# One record per bird

This is the specification for a future species catalogue, not a newly implemented backend schema. Keep the illustration identity, anatomical registration and choreography together. A generation prompt is only one field in that record.

| Record group | Required information |
|---|---|
| Identity | Stable species ID, common/scientific names when verified, sex/age/plumage if relevant, diagnostic features and their sources |
| Art source | File, crop if needed, source hash, generation/edit prompt, image-tool/model/version if available, references used, review status |
| Composition | Artistic intention, facing, pose, character decisions, open creative choices, placement, colour relationships and optional background elements (none, one or multiple) |
| Registration | Bird silhouette polygon(s), head/body/wing/tail geometry, sketch paths, paint-region polygons and flow direction, extras, excluded and focal areas |
| Materials | Wet-region entry points and coverage, pigment character, brush breadth/load, dry-pencil regions; shared defaults with explicit overrides |
| Choreography | Initial gesture, order of regional visits, per-region broad/medium/fine windows, perceptual time mapping, meaningful feature reserved for the last ten seconds |
| Reproduction | Renderer/profile version, source bytes and hash, seed, fluidity, duration, approved reference frame and checkpoints |
| State treatment | Name layout and separate activity/health annotation; the source may contain an illustrative state that must not be mistaken for sensor data |
| Review | Proposed / trial / accepted, final fidelity notes, anatomy check, visible-progress check, playback behavior and any material limitation |

## Coordinate conventions in the existing renderer

Registration uses a **1000×750** drawing space. The source image can have a different resolution.

- `sourceCrop` and `destRect` use `[x, y, width, height]`.
- Region boxes use `[x0, y0, x1, y1]`.
- Polygons and path points use `[x, y]`.
- Anatomical ellipses use centre, radii and rotation in radians.
- Named `paintRegions` describe actual anatomy, not equal rectangles cut through the picture.
- `backgroundGeometry` is descriptive metadata; current painting reconstruction samples inside `backgroundBoxes`. Changing the metadata alone does not redraw the background.

Read the bundled `assets/runtime/species-config.json` for real examples. It contains existing registrations for Robin, Blue tit, Blackbird and Wren. Those other registrations came from the 90-second collection; they are useful starting geometry, not approved 75-second motion profiles.

The Robin retimer additionally uses a decorative-wing ellipse and coordinate-based feet/perch classification. These are implementation details to replace with each bird's regions. Do not stretch the Robin's map onto the Wren, or remove the Robin-only guard and assume the sequence generalises.

## Managing a larger collection

Keep one shared material/renderer version and one record per artwork/pose. A species with two genuinely different poses needs two registrations. Store revisions rather than overwriting accepted art.

Use an optional overview with only the fields needed to spot repetition: bird, silhouette/pose, dominant palette, background shape/offset, character emphasis, motion variant and review status. Reusing a shape is fine; repeating the entire composition across many birds is not.

Do not fabricate encounter counts, local presence, species facts or unavailable model metadata to fill fields. Record unknowns plainly.

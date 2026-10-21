# Retained status graphics

The files in `references/` are byte-for-byte copies of the original design examples: perspective circular ripples, the unplugged pie, the “Singing now” corner and the Pi-disconnected corner. They are visual references, not live sensor evidence. Their hashes are in `../import-snapshot.json`.

`status-marks.svg` copies each existing `<symbol>` from `static/display.html` verbatim. It preserves the connected player's implemented ripple, memory, local, disconnected-pie and microphone graphics. The standalone sprite is reusable; the player still uses its existing inline copy.

For example: `<svg viewBox="0 0 100 58"><use href="status-marks.svg#mark-pie"/></svg>`.

Keep activity and equipment health separate. “Singing now” belongs only to evidence that supports current activity; a single past detection cannot prove ongoing song throughout a 75-second painting. The connected player currently uses “Heard just now” for recent detection, then last-heard information. Preserve the requested original artwork and wording as design references without baking a false live claim into every portrait.

A disconnected pie means stale/missing Pi reporting; it does not mean a quiet garden. A listening failure is separate. The brushstroke progress measures painting playback. Healthy listening does not need an additional permanent corner label.

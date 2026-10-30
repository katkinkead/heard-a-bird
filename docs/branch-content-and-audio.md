# Branch content, audio and evidence

Implemented 23 October 2026 in the existing Songsketch server. The original five-bird portrait catalogue and approved painting assets remain unchanged.

## Display and content

The branch, single-bird and infographic views share the period read model. Completed portraits receive names, bout counts and current activity marks. The infographic now adds one short, sourced fact per featured or supporting bird; branch captions stay uncluttered. All 45 species have a fact record in `artwork/branch/content.json`. The small menu links to a searchable local source/recording-credit library.

Gold and holographic feathers reuse the approved transparent artwork. Gold means regional scarcity, not conservation concern. The four owl candidates use dated Dorset county evidence (2021–22), visibly identified in the source library and operator evidence. Their classifications need comparison with the newest county report before deployment; this is not a 2026 population estimate.

Holographic means unusual *for this garden*. The provisional rule requires:

- The species is inside its curated seasonal window.
- At least 30 earlier comparable calendar days have four hours of confirmed healthy listening each.
- Comparable days are within 45 calendar days of today’s seasonal position, across up to two years.
- The species was detected on no more than two of those earlier days.

Today is excluded. Short listening days, test detections, unconfirmed heartbeat tails and history erased by retention cannot establish absence. Cleanup records a monotonic history floor, so increasing retention later does not revive missing records as evidence of silence. The baseline is cached for at most 30 seconds and invalidates on practice reset, date, timezone or retention change. Seasonal exceptions remain in history; they do not automatically get the unusual badge. Thresholds are explicit starting values requiring field validation, not a statistical rarity model.

## Audio

Local playback works without provider credentials or network access. All 45 illustrated species now have a locally packaged natural reference recording, including Tawny, Barn, Little, Short-eared and Long-eared owls. Sources are Wikimedia Commons, including British Library recordings and recordist-licensed Xeno-canto recordings mirrored there. Licences are CC BY, CC BY-SA or public domain, recorded individually with creator, source, edits and checksum in `artwork/branch/content.json` and `artwork/branch/audio/CREDITS.csv`. MP3 metadata also contains the attribution. Adapted share-alike clips retain the source licence.

The weak Chaffinch sample was replaced by an archived British song recording. Earlier speech, imitation and synthetic-chorus candidates remain excluded. Excerpts last up to 12 seconds; short source recordings are not looped. Natural pitch and timing are retained, with mono conversion, loudness adjustment and gentle fades.

The Pied Wagtail entry is a Swiss White Wagtail (*Motacilla alba*) species reference, not a confirmed recording of the British *yarrellii* subspecies. Great Spotted Woodpecker uses drumming; the Rook clip includes natural rookery ambience. These qualifications are shown in the listening library. Songs, calls and drumming are reference sounds, not evidence of what a particular garden detection was doing. All 45 MP3s passed decoding, duration, non-silent signal and checksum checks. Full listening on the intended speakers and microphone-feedback commissioning remain.

The small menu contains sound enable/mute and volume. Each newly opened display starts muted; enabling sound is a browser user gesture. Volume is retained locally. A refresh does not replay existing bouts. One fresh bout can play one clip, with no fixed cooldown, no overlap and no delayed queue. New species wait for their painting to start; if the bout is already over 60 seconds old when assets become ready, its audio is skipped. Repeat bouts can play without repainting. Mute, unavailable listening or lost server contact discard pending playback. Clip failures leave the painting running.

Audio is a reference recording, not the live microphone. Use one designated sound-producing display. Speaker placement, loudness and whether the garden microphone hears these clips require physical commissioning; no feedback suppression is claimed.

## Operator evidence

Garden desk → Activity & evidence uses authenticated `/api/admin/branch-evidence?period=day|week|month`. It shows bouts versus accepted classifier observations, confirmed and unconfirmed listening hours, median/95th-percentile delivery delay, local sunrise/sunset, library readiness and the reason behind every unusual/regional decision. Delivery statistics sample the latest 2,000 accepted observations in the selected period. Basic library source information is public; operator diagnostics remain authenticated.

## Verification

The full suite passed 279 Python tests after the retention regression was added. Separate JavaScript checks exercise audio deduplication, no overlap/backlog, mute, stale server state, painting-start playback and repeat bouts; display completion and repeat-caption regressions also pass. The layout sweep still passes 405 cases.

Actual browser verification: Robin repeat-bout playback reached “Reference clip finished”; five completed birds showed their captions and a small gold feather beside Barn owl; the sourced carousel and library rendered without browser errors. The new authenticated evidence endpoint is covered by HTTP tests. The dashboard navigation and locked state were inspected; an authenticated dashboard screenshot was not captured in this pass.

Restore tests exercise the actual CLI into a fresh runtime, history/art recovery, credential preservation, held target locks, hostile paths and rollback after an injected copy failure. SMTP tests use real sockets into a loopback-only, non-forwarding sink: delivery, duplicate suppression, recipient refusal/recovery and lost acknowledgement. These do not prove external SMTP, TLS/auth or inbox receipt.


24 October audio completion: all 45 source/credit records and local MP3s verified; see `qa-evidence/branch-rehearsal/audio-library-verification.json`. The audio inventory regression verifies catalogue coverage, file integrity and matching distributed credits.

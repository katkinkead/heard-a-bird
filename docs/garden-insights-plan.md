# Heard a Birdy — garden insights and a future garden network

30 October 2026. Repository audit and proposed design, not an implementation or field-validation report. Builds on the existing Garden desk rather than replacing it. Public name: Heard a Birdy; repository/application name: Songsketch.

## Purpose

Help someone understand their own garden: which species they hear, when they are active, which return, and what appears to change through the seasons. Let the artwork invite attention and the dashboard explain the observations behind it. Longer term, offer an opt-in network of gardens that can reveal broader patterns with appropriate quality controls and privacy.

## What is in the code today

| Capability | Evidence | Current limit |
|---|---|---|
| Species list, search, first/last heard, distribution and CSV | `static/dashboard.js`: `renderDiversity`, `renderBirds`, export handler; `songsketch/store.py`: `summary` | Month/all-time selector; totals are accepted classifier detections, not bouts. No prior-period comparison. |
| Day/week/month species, bouts and matches | `static/dashboard.js`: `renderEvidence`; `songsketch/branch.py`: `snapshot` | Separate evidence tab; not the main garden overview. Counting thresholds are provisional. |
| Confirmed/unconfirmed listening hours and delivery delay | `songsketch/bird_content.py`: `coverage`, `evidence` | Aggregate text rather than a navigable coverage timeline or comparable-period insight. |
| Seasonal unusualness and regional rarity explanations | `songsketch/bird_content.py`: `baseline`, `decision` | Curated regional content is not a regional observation network. Current provisional baseline requires 30 comparable days with at least four listening hours each; it does not establish comparable time-of-day coverage. |
| Local sunrise/sunset | `songsketch/branch.py`: `solar`; evidence tab | Useful context exists; no activity-by-solar-time chart. |
| Separate capture/inference/connectivity status, test capture exclusion | Dashboard health and capture controls; `songsketch/capture_exclusion.py` | Hardware audio quality and outdoor performance still require physical testing. |
| Station-labelled detections | `songsketch/store.py` schema and ingest | Ingest is configured for one station; listening windows lack station/site IDs. Not a multi-garden backend. |

The older planning documents describe some of these as pending. The code above supersedes those historical status descriptions. No browser or automated tests were rerun for this read-only audit.

## Proposed Garden desk experience

The default view should answer a few clear questions, with maintenance, artwork management and technical evidence available separately.

### 1. What has my garden sounded like?

Use a shared day/week/month/custom-range selector. Lead with species heard, separate bouts, days monitored and confirmed listening hours. Keep classifier matches available in evidence rather than presenting a second competing headline count. A bout is grouped acoustic activity, not an individual bird or confirmed visit.

Show a small number of computed, inspectable insight cards. Examples are copy patterns only, never fabricated observations:

- “First recorded here: [species], [date].” Say first **recorded**, not newly arrived; disclose the retained-history boundary.
- “[Species] was heard on [n] of [m] sufficiently monitored days.” Expand to show the coverage definition and observed dates.
- “Most recorded activity this week: [species].” Explain the measure; do not imply population size.
- “Too little comparable listening time to assess change.” Treat this as a useful answer, not an empty error state.

### 2. What has changed?

Compare the selected period with an equivalent previous period; offer prior-year seasonal comparison only once enough retained evidence exists. Today-so-far must not be compared blindly with a full previous day, or a partial month with a complete month.

Compare acoustic activity using bouts per confirmed listening hour only where numerator and denominator cover the same intervals. Show counts and hours beside rates. Exclude or explicitly separate observations outside confirmed coverage. A raw rate is not enough: differences in morning/night coverage, microphone placement, model, threshold and season can change results.

Do not divide species richness by hours and call it a corrected biodiversity measure. Show observed species alongside effort and use matched observation windows or a separately validated method for comparison. Suppress strong trend language for small samples, major coverage gaps or changed equipment/settings.

### 3. When is the garden active?

Provide an activity heatmap by garden-local day and hour, with a species filter. Include listening coverage in each cell: no listening evidence must look different from monitored time with no accepted detections. Allow dawn/day/dusk/night or time-relative-to-sunrise exploration using the existing solar calculation. Keep raw counts and effort-adjusted rates clearly selectable and labelled.

### 4. Who returns, and who is unusual here?

A species detail view should combine its portrait, first recorded date, latest detection, days heard, bouts, daily activity history, seasonal context and the records behind any unusualness assessment. Separate regional rarity, garden unusualness and conservation status.

Improve comparison coverage before presenting unusualness as a robust ecological conclusion: four daytime hours do not establish that an owl was absent overnight. Preserve “baseline developing” and the provisional status of thresholds. An out-of-season classification remains reviewable evidence; it does not automatically earn the agreed unusual-visitor badge.

### 5. What have I changed in the garden?

Optional future local feature: a garden diary for planting, pond installation, mowing, feeders or microphone relocation. Overlay these dates with activity histories. This supports questions and observation, not claims that a particular action caused a change. Record microphone moves as data-quality changes, not only diary notes.

## Trustworthy calculations and UX

- Reuse a single versioned bout definition across the artwork, overview, species detail and exports. Keep source observations and timestamps inspectable.
- Define interval attribution and period-boundary treatment so a continuous bout crossing midnight is not accidentally represented as two independent encounters in a regional export.
- Distinguish observation time from server receipt; delayed delivery repairs history without becoming live activity.
- Keep test/synthetic data and commissioning recordings out of garden insights and seasonal baselines. Retain quality and exclusion reasons.
- Keep confidence as a model score; do not describe it as a calibrated probability that the bird is present.
- Make source recordings optional and consent-aware. Add review/correction provenance before confidently publishing exceptional records.
- Record model, threshold, microphone/configuration changes and history retention limits. Preserve unknown values for historical records rather than inventing provenance.
- Every insight can open its underlying records, period, rule, coverage and limitations. Prefer deterministic summaries to unsupported AI interpretations.
- Rename the current diversity section in user-facing copy to “Recorded species” or “The shape of the chorus”; avoid a garden biodiversity score.

## Future regional network — explicit intent, not built

The existing local data store and CSV are a starting point, not a shared research network. Build regional participation as an additional, voluntary layer.

Before collection, define site IDs separate from device IDs, device replacement history, site-specific monitoring windows, taxonomy identifiers, UTC times plus local timezone, model/configuration versions, confidence and review status, and microphone/setup metadata. Local detection deduplication by station/event is not cross-garden bird identification: two gardens may hear the same bird.

Require explicit opt-in, purpose and retention choices, withdrawal/deletion, and garden-level access control. Protect precise household locations; regional presentation should use appropriate geographic aggregation and sensitive-species rules. Do not upload raw audio by default or assume recordings are free of human speech.

Potential regional views:

- Species recorded across participating gardens, with the number of monitored gardens and their listening coverage.
- Seasonal timing and daily activity patterns across comparable locations.
- Changes in recorded species distribution, labelled with sampling gaps, device/model differences and review status.

Do not publish a leaderboard of “most biodiverse gardens,” equate raw detection totals with abundance, or claim population trends from an uneven voluntary sample. Agree validation, licensing, ethics and export requirements with any research/conservation partner before claiming compatibility or contribution to its dataset. No external integration or partner commitment exists yet.

## Efficient implementation order

1. Agree dashboard questions and metric definitions; align current raw-match versus bout presentation.
2. Build shared date-range and per-interval coverage/aggregation queries; preserve existing operational pages.
3. Add overview insights and species details with clear empty/insufficient-evidence states.
4. Add activity-by-time and matched-period comparison, then garden diary if useful.
5. Validate with labelled scenarios: quiet-but-listening, absent monitoring, unequal coverage, midnight/DST, owl/daytime mismatch, late/duplicate records, test capture, retention and changed settings. Use simulated labels until genuine garden observations exist.
6. Review on real garden data and equipment. Adjust wording and provisional thresholds from evidence.
7. Design a separate opt-in regional data contract and pilot. Do not silently centralise local history.

This audit adds design requirements only. The new insights, charts, diary and regional network described above have not been implemented by this revision.

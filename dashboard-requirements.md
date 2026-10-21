# Songsketch bird history and missing artwork dashboard

> Implementation update, 21 October 2026: the local MVP is now built in this repository. This file preserves the design requirements; see [README](README.md), [feature map](docs/features.md) and [verification record](docs/verification.md) for the implemented scope and remaining hardware/provider checks. Earlier future-tense notes below are historical planning, not current build status.
Updated 21 October 2026. Requirements for the MVP build; the dashboard and email delivery are not implemented yet.

The server should retain bird detection history and provide a dashboard showing activity over time. When a detected species has no artwork, the dashboard should flag it and the server should email the friend responsible for setting up Songsketch.

## Bird history

Store detections independently of whether they trigger a painting. Display cooldowns must not discard bird history. Retrying delivery of an existing detection must not inflate its count.

The proposed dashboard should provide:

- A chronological detection history with common and scientific names, detection time, confidence and station.
- A species summary showing first heard, last heard, monthly activity and total activity, with date filters.
- Artwork coverage for every species heard, including a filter for missing artwork.
- Notification status for missing artwork, including queued, sent or failed delivery.

Counts must state what they measure. Raw detections and grouped encounters are different measures; neither is a count of individual birds. The encounter grouping rule and historical data retention should be defined before implementation. Store timestamps consistently and display garden activity in Europe/London time.

## Missing artwork email

The recipient should be a configurable setup contact. Katharine has specified her friend who will set up the project; their email address still needs to be supplied when email delivery is configured. No message is being sent as part of recording this requirement.

The proposed default is one email when a species first qualifies as a real detection and lacks approved artwork. The message should identify the species, when it was heard, its confidence and the missing-artwork status. Include a dashboard link when the recipient has a usable route to that dashboard; the email itself should contain enough information to be useful without opening it.

Repeated detections should update the species history and missing-artwork entry without sending another email for each detection. Use a persistent notification record to avoid duplicates after ordinary retries or service restarts. Failed delivery should remain visible and retry when the mail service becomes available; email failure must not interrupt recording or painting. Repeated reminders are not enabled by this requirement.

When approved artwork is added, resolve the missing-artwork entry while preserving the detection and notification history. Track animation readiness separately so artwork that has not yet been prepared for playback is not presented as a working animation. A missing animation alone should not be labelled as missing artwork.

During missing-artwork cases, the display should continue using available approved artwork. New artwork creation remains part of the review and approval workflow.

## Optional AI tools

The dashboard should offer optional actions that the setup contact can trigger deliberately. AI actions remain unavailable until the relevant provider credentials and supported model capabilities are configured; local reference browsing and prepared animation previews remain available without a key. Saving credentials alone must not start a job, schedule recurring AI work or generate artwork for every detection. These workflows still need implementation; an API key does not provide them by itself.

| Dashboard action | Proposed result | AI requirement |
| --- | --- | --- |
| Diagnose this issue | Explain a selected diagnostic report and propose repair steps | A configured text or reasoning model |
| Generate artwork draft | Produce a species concept using the approved style guide and actual reference images | A configured image generation model |
| Prepare animation draft | Help author anatomical registration, drawing paths, paint regions and timing for approved artwork, then build a local preview | A configured model for assisted authoring; the build and playback are local code |
| Suggest style guide update | Draft a versioned change using selected approved examples and the operator's direction | A configured text or vision model |
| View or organise style references | Browse and manage the existing local reference library | No AI required |
| Rebuild or preview a prepared animation | Reuse saved artwork, registration and choreography | No AI required |

Normal detection handling, history, playback, report collection, email templates and routine recovery should continue without AI credentials. Email delivery has its own mail configuration. An image-generation API produces image assets, not this project's authored 75-second brushstroke sequence; the animation-authoring workflow must be implemented and evaluated before it is presented as ready. Existing approved reference files and the guide remain bundled locally without regeneration. See the [painting implementation notes](artwork/painting-system/references/implementation.md) and [OpenAI image generation documentation](https://developers.openai.com/api/docs/guides/image-generation).

### Credentials and action copy

Use an optional AI settings panel with the provider, supported functions, a masked credential status and controls to test, replace or remove credentials. Restrict credential management and paid actions to the installation's administrator. API requests should run on the server with credentials stored in protected server configuration or a secret store, excluded from browser storage, delivered frontend code, logs, exported reports and ordinary project backups. OpenAI's [authentication guidance](https://developers.openai.com/api/reference/overview#authentication) requires keeping API keys out of client-side code. Local setup can accept the key through a protected administrator flow; the public artwork display must never receive it.

Proposed notice when AI is not configured:

> Optional AI tools need your own provider API key and may incur usage charges. Add a key in Settings to enable supported tools. Existing bird playback and routine recovery work without one.

Before a run, show the selected provider, what images or diagnostic information will be sent, and the applicable spending limit. Show an estimate where one is available without promising an exact price. Art jobs should identify the chosen source artwork and style version. Diagnostic jobs should send only the selected report with secrets removed. No provider credentials or user data are being submitted by recording these requirements.

### Drafts and review

Every AI job should have a persisted status, useful progress messages, a result or clear error, and bounded retries and spending. Record prompts, reference versions and output files. A failed or interrupted job must not silently repeat paid requests indefinitely or disrupt the live display.

Generated artwork and animations remain drafts until reviewed and approved. The animation preview should include milestone and final-image checks against the project's existing renderer and timing standards. Failed checks should leave a draft needing correction. Style updates should show the proposed change and preserve the previous version; existing approved birds and the Robin benchmark should remain intact.

AI diagnosis should produce an explanation and a proposed repair. Applying a repair is a separate action with a recorded change and recovery path. Defined routine recovery remains automatic; accepting arbitrary model-generated commands as unrestricted server maintenance is outside this workflow.

## Acceptance checks for the build

1. Detect a species with approved artwork: its history updates without a missing-artwork email.
2. Detect a new species without artwork: a dashboard entry and email notification are created automatically.
3. Repeat that detection and retry the original event: genuinely new detections update history, retried events do not inflate counts, and no repeated missing-artwork email is triggered.
4. Make email delivery unavailable: the notification remains pending, recording and display continue, and delivery retries after recovery.
5. Add approved artwork: the missing-artwork flag resolves without losing bird history; animation readiness remains accurate.
6. Start with no AI key: playback, history and routine recovery work; AI actions show the setup notice and make no paid requests.
7. Configure a supported provider: only explicitly started AI jobs run, using server-side credentials and the selected inputs.
8. Generate a draft: it remains outside the live catalogue until approval, and its prompt, references and validation results are retained.
9. Remove credentials or exhaust the configured budget: additional AI calls stop while normal display and reporting continue. A request already accepted by a provider may still complete and incur a charge.

## Related requirements

Automatic diagnostic uploads, offline report downloads and server recovery are specified in [automatic reporting and maintenance](maintenance-requirements.md). Bird activity, missing artwork and operational faults should be distinguishable within the dashboard.

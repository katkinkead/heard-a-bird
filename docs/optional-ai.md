# Optional AI at the art table

Everyday playback, history, missing-art emails, backups, report delivery and defined recovery use local code. They do not need an AI key.

The dashboard accepts an operator's OpenAI API key only from the server's localhost administrator session. The key stays in an owner-readable file outside the repository. It is never returned to the dashboard or exported in reports/backups. Removing the key stops future jobs; a request already accepted by the provider can still finish and incur a charge.

Each job requires a deliberate confirmation describing the information sent. At most one provider request is made per job, with no automatic paid retry. A rolling24-hour job cap defaults to3. Text output is capped at3500 tokens; artwork requests one medium-quality image. These are request/output limits, **not a guaranteed dollar cap**. Configure provider account budgets/limits and check current model pricing before use.

The initial model fields are configurable. Account/model availability is verified only when a real request is made. No paid request was made during this build.

- **Diagnose:** sends the redacted support bundle for an explanation and proposed steps. No suggested commands are executed.
- **Portrait:** sends the bundled actual Robin, Goldfinch and collection images, the versioned style system and the species/direction to the image-edit endpoint. The output remains a draft. Review anatomy and design before approval. Approval adds a new still image with `animation_ready:false` and never overwrites a packaged species.
- **Style:** creates a proposal beside the current guide; it does not rewrite the approved language.
- **Animation:** sends approved artwork and implementation notes to author a registration/choreography proposal. Existing prepared animations can be previewed immediately. A new species still needs the registered anatomy, brush paths, local build and milestone/fidelity validation described in the painting skill before playback approval. This action does not invent a finished animation or run model-generated code.

Requests, style hashes, reference filenames, results and provider usage (when returned) are saved in the protected draft folder. If a process dies during a provider request, the job becomes failed/needs review on restart, without submitting it again. Check the provider account before retrying an uncertain paid request.

Implementation follows the official [image generation guide](https://developers.openai.com/api/docs/guides/image-generation), [image edit API](https://developers.openai.com/api/reference/resources/images/methods/edit) and [text generation guide](https://developers.openai.com/api/docs/guides/text), checked21October2026. The API returns images/text; Songsketch's authored75-second painting renderer is a separate local component.

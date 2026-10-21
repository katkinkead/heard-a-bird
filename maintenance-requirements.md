# Songsketch automatic reporting and maintenance

> Implementation update, 21 October 2026: the local MVP is now built in this repository. This file preserves the design requirements; see [README](README.md), [feature map](docs/features.md) and [verification record](docs/verification.md) for the implemented scope and remaining hardware/provider checks. Earlier future-tense notes below are historical planning, not current build status.
Updated 21 October 2026. Requirements for the MVP handover and final connected installation; implementation and hardware verification remain pending.

Songsketch should send bug reports to its indoor server automatically and recover from routine faults without someone downloading reports or managing services. Downloadable reports remain available as an offline fallback. This records Katharine's clarification and the proposed implementation needed to support it.

## Report delivery

The Pi should save each diagnostic report locally before attempting delivery to the server. When connected, it should upload automatically. When the network or server is unavailable, it should retain pending reports across restarts and retry after reconnection. A local download should remain available when the Pi is reachable directly, even if it cannot reach the server.

The server should acknowledge a report only after storing it durably. A stable report ID should prevent retries from creating duplicate incidents. Repeated occurrences of the same fault should be grouped and rate limited, with the first occurrence, latest occurrence and recovery recorded. Reports should exclude passwords, tokens and API keys.

Reports should include the fault, affected component, relevant recent logs and health readings, recovery actions attempted, and their outcomes. Server faults should be recorded locally and appear alongside Pi faults after recovery.

## Automatic maintenance

The proposed implementation should:

- Monitor the Pi connection, audio capture, recognition service, relay, server and display connection separately. A quiet garden is healthy; a heartbeat alone does not prove that the microphone or recognition is working.
- Restart failed services and retry interrupted connections using bounded attempts and increasing delays. Record recovery attempts and verify that the affected function works again.
- Run the server application under an operating-system supervisor so an application crash can be recovered without the application itself running. Services should return automatically after a reboot.
- Rotate logs, bound diagnostic storage, and maintain database backups with defined retention. Surface storage or backup failures before they prevent recording new detections.
- Preserve detection history, queued reports and approved artwork during recovery. Keep the last available painting on screen during recoverable interruptions.
- Show unresolved faults on the maintenance page and support notifications for problems that need attention. Notification destination and channel are still to be chosen; no external notification service is configured by this note.

Automatic maintenance covers defined recovery procedures and does not require an AI model or API key. The dashboard should additionally offer an optional, operator-triggered AI diagnosis action using configured provider credentials. It should explain selected diagnostics and propose repair steps; applying a repair is a separate action. These AI workflows remain to be built, as described in the [dashboard requirements](dashboard-requirements.md#optional-ai-tools). Routine recovery must continue when AI is disabled or unavailable.

If the server computer loses power, its application cannot notify anyone at that moment. The Pi should continue buffering reports while it is powered. Immediate notification of a completely failed server would require a separate monitor; the MVP should at least recover and reconcile reports when the server returns.

## Acceptance checks for the build

1. Trigger a controlled Pi fault while connected: a report appears on the server without manual download or upload.
2. Disconnect the server, create a report, and restart the Pi: the pending report survives, remains downloadable locally, and uploads once after reconnection.
3. Crash the server application: its supervisor restarts it, records the interruption, and accepts queued reports without duplicate incidents.
4. Reboot each device: services return automatically, stored detections remain intact, and pending delivery resumes.
5. Simulate a persistent fault: recovery attempts back off, reporting stays bounded, and the maintenance page clearly identifies the unresolved problem.
6. Leave the garden quiet while capture and recognition remain healthy: no false failure is raised.

## Guide integration

The consolidated setup guide should verify automatic report delivery and recovery, with downloads presented as the offline fallback. Claude's existing guide already describes automatic uploads and retries in step 8; the packaged software and guide should preserve that behaviour and extend it to server recovery. This local requirement capture does not change the published Claude artifact.

Bird history and automatic emails to the setup contact about missing artwork are specified in [bird history and missing artwork dashboard](dashboard-requirements.md).

# Heard a Bird — 30 October 2026 repository snapshot

The GitHub repository is now `katkinkead/heard-a-bird` (private), previously `katkinkead/songsketch`. Package names, service paths and existing runtime data directories retain Songsketch for compatibility. The current launcher uses the new repository and accepts old origins only for existing managed checkouts; unrelated origins remain rejected.

This snapshot collects the existing branch implementation, approved art/audio assets, local setup refinements, display reporting, recovery and their tests. It does not promote simulated hardware evidence into physical commissioning.

Validation on 30 October 2026: all **291 Python tests passed**, including the renamed-repository compatibility regression. The launcher and its executable-preserving ZIP were regenerated from their source. Browser demo work lives in the separate submission-site checkout and is not the Python production server.

## A tester without a Pi

The executable Practice Garden already exercises the real application with synthetic Pi messages. See [simulation](simulation.md). It uses separate state and cannot SSH into a device or send external email/AI jobs.

The real ARM64 BirdNET lab has also processed recorded audio, persisted detections and delivered them through the production relay. See [its exact evidence and reproducible checks](birdnet-live-validation.md).

A clean VM rehearsal of the complete Pi installer is still pending. A generic ARM64 Linux VM is not a Raspberry Pi: it cannot validate Pi firmware, USB microphone capture, physical Wi-Fi, power or the enclosure. The next installation test should use a disposable, isolated Linux VM with a supported service manager, real SSH identity verification, private test credentials and real BirdNET; keep Pi hardware guards intact and record any unsupported checkpoint rather than bypassing it. The setup UI should report actual probe/configuration/service checks, not play a prewritten success animation.

For submission reviewers, offer the browser product demo first and the Practice Garden as an optional local download/repository exercise. Do not require a paid AI account or a VM just to watch the product. A full software-installation lab is a deeper engineering test, not yet a one-click judged outcome.

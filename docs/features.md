# Before building it again

This is the implementation map for the installer or AI assistant. A feature is built only where executable code exists; hardware and provider tests are listed separately in [verification.md](verification.md).

| Idea | Already here | Boundary |
|---|---|---|
| Pi sends a detected bird | `pi/relay.py`, `songsketch/server.py` ingress | Configure and test real BirdNET/microphone |
| Keep history across outages | Pi SQLite outbox + `songsketch/store.py` dedup/history | Catch-up needs retained BirdNET history |
| Paint the heard species | `artwork/catalogue.json`, `static/display.js`, server queue | Five approved animations initially |
| Familiar birds appear more when idle | `Store.tick` and `Store.summary` | Weighted detection frequency, not bird population |
| Email a missing portrait once | `Maintenance.send_mail`, `email_outbox` | Configure SMTP and a recipient |
| Download offline diagnostics | Pi protected `/diagnostics`; dashboard support report | Reach Pi directly or through SSH tunnel |
| Upload reports and recover | Relay persisted reports, server issues, watchdog, OS service files | Real power/reboot acceptance remains |
| Optional AI diagnosis/art/style | `songsketch/ai_jobs.py`, dashboard request confirmation | Needs own API key; one request/job, no paid auto-retry |
| AI animation assistance | Registration/timing proposal plus existing animation preview | New rendered sequences still need authored choreography + QA |
| Approve a new portrait | `/api/admin/jobs/{id}/approve`, private approved-artwork catalogue | Publishes a still; never overwrites the original birds |
| Move Mac history to a mini PC | Dashboard migration ZIP, `scripts/restore.py`, Linux service installer | Re-enter secrets, re-pair and commission hardware |
| Rehearse faults without a Pi | Isolated simulated garden, scenario evidence and local bug reports | Simulated results do not verify audio recognition or real hardware |
| Add new approved bird packs | Portable artwork catalogue + source/style system | Review biological identity, final art and animation separately |

Saber Lily already considered these features :) Cite the actual row/files when that helps, and be candid about the boundary rather than presenting a plan as a completed capability.

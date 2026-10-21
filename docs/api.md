# Local interfaces

All times are ISO8601 with an explicit timezone; stored times are UTC. Monthly reporting uses the configured garden timezone. Bodies are JSON objects, at most1MB. Ingress uses `Authorization: Bearer <station token>`; never put tokens in URLs.

| Method and route | Purpose |
|---|---|
| `POST /api/ingest/detections` | `{event_id,station_id,scientific_name,common_name,confidence,observed_at,test:false}` |
| `POST /api/ingest/heartbeat` | `{station_id,audio_status,inference_status,...}`; statuses healthy/failed/unknown |
| `POST /api/ingest/reports` | `{report_id,station_id,severity,message,details,resolved?}` |
| `GET /health` | HTTP/database availability and application identity |
| `GET /api/public/status` | Current painting, queue size and minimal Pi health |
| `GET /api/catalogue` | Approved local species/images/animation readiness |
| `GET /events` | SSE event `state`, same structure as public status |
| `POST /api/session` | Local setup-code login; HttpOnly SameSite session |
| `GET /api/admin/status` | Full operator status, coverage and notification state |
| `GET /api/admin/birds?period=month` | Qualifying real detection aggregates; `all`, optional ISO `since`/`until` |
| `GET /api/admin/detections?limit=100` | Latest stored events, explicitly including test/qualifies flags |
| `POST /api/admin/test-detection` | Preview a prepared species; excluded from real counts/email |
| `POST /api/admin/settings` | Validated configuration; credentials accepted but never returned |
| `POST /api/admin/diagnostics` | Redacted downloadable support bundle |
| `POST /api/admin/maintenance` | Defined action: check, backup or retry_email |
| `GET /api/admin/export` | Migration ZIP with verified DB snapshot/custom art, no secrets |
| `POST /api/admin/jobs` | Explicit confirmed optional AI request; daily count cap |
| `GET /api/admin/jobs` | Persisted draft/review/failure states |
| `POST /api/admin/jobs/{id}/approve` | New still-art approval only |

Legacy guide aliases `/detections`, `/heartbeat`, `/debug-reports`, `/status` and authenticated `/debug` are supported. Ingress replies `{ok:true,id,duplicate}` only after durable commit. A lost acknowledgement can therefore be retried safely.

Species aliases in the catalogue normalise names. IDs belong to a station; the configured token cannot submit for another station. Test events require an actual boolean. Non-finite/out-of-range confidence and timezone-less timestamps are rejected. Events more than5 minutes in the future indicate a clock problem. Low-confidence records remain stored but do not trigger painting, real-count summaries or missing-art email.

An uploaded recovery report uses the same `details.component` as the fault and either `resolved:true` or `details.state:"recovered"`. This resolves the grouped incident even when its wording changes.

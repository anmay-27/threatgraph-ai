# API

Interactive schemas: `http://localhost:8000/docs`; OpenAPI: `/openapi.json`.

| Method / route | Behavior |
|---|---|
| POST /api/v1/analyze/url | JSON `{ "url": "https://example.com/" }`; returns 202 `{id,state}` |
| POST /api/v1/analyze/file | Multipart `file`; streams to generated filename, enforces size cap, sniffs bytes |
| GET /api/v1/analyses/{id} | Metadata, real progress, state, full report |
| GET /api/v1/analyses/{id}/status | State and completed step log |
| GET /api/v1/analyses/{id}/graph | Nodes/edges |
| GET /api/v1/analyses/{id}/evidence | Standard evidence objects |
| GET /api/v1/analyses/{id}/media | Preview for supported media while retained; HTML is never previewed |
| GET /api/v1/history | Search/filter: q, input_type, risk, verdict, after, limit (maximum 500) |
| GET /api/v1/dashboard | Counts/distributions derived from database records |
| GET /api/v1/models | Installed model metadata and explicit unavailable entries |
| GET /api/v1/health | Database connectivity, privacy and queue configuration |

States: QUEUED, PROCESSING, COMPLETED, PARTIAL, FAILED. COMPLETED does not mean safe. PARTIAL retains findings when scanners/models or network requests fail. Poll analysis/status until a terminal state; the frontend polls every 1.5 seconds. Progress is recorded after actual steps; no synthetic timers.

Missing score is `null` and overall risk may be `null`/UNKNOWN where no scored evidence exists. Risk labels use 0–24 LOW, 25–49 MODERATE, 50–74 HIGH, 75–100 CRITICAL. Confidence and uncertainty are separate fields. High uncertainty, conflict, OOD, or incomplete coverage yields INCONCLUSIVE.

Responses: 404 unknown ID, 410 expired media, 413 too large, 415 unsupported preview, 422 invalid input, 429 submission limit, 503 unavailable queue. Local development is single-user with no auth; do not publish these endpoints without an authenticated gateway. History filtering currently applies risk/verdict after a bounded database selection, so it is not a complete pagination API for large archives.

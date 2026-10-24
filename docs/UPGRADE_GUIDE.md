# Investigation upgrade: reviewer guide

The current upgrade extends the existing ThreatGraph codebase. It does not retrain or replace the image, video or URL models.

## Use the new workflow

1. Start the native development API and frontend as described in [DEPLOYMENT.md](DEPLOYMENT.md), or use Docker with account mode enabled. Register and promote your account to `ANALYST` using the command in that guide.
2. Open **Message / email**, paste a harmless sample such as `Job offer: a registration fee is required before onboarding. Contact recruiter@example.org.` Submit it.
3. Open the report. Review the recruitment scenario, its supporting evidence, missing verification and action to contact the employer independently. AI origin and risk remain separate.
4. Create **Job Offer Investigation** under **Cases**. Add the message analysis from the Analyses tab. Add an investigator note, check Timeline and Threat graph, and export the case PDF.
5. Search `example.org` in **Intelligence graph**. Open the entity to see this occurrence and any other permitted investigations containing it.
6. For the complete controlled email→PDF→QR→URL parser chain, run `python -m pytest backend/tests/test_upgrade_workflows.py`. The test substitutes only the remote HTTP response with harmless HTML; the email parser, PDF renderer, QR decoder, URL traversal, evidence graph and scenario rules run normally. No malicious payload is shipped.

Existing historical reports can be indexed with `.venv/Scripts/python.exe scripts/index_historical_entities.py` from the workspace root after the additive schema migrations. It neither reruns detectors nor fetches historical URLs.

## New endpoints

| Area | Endpoints |
|---|---|
| Cases | `GET/POST /api/v1/cases`, `GET/PUT/DELETE /api/v1/cases/{id}`, `POST /api/v1/cases/{id}/notes`, `POST/DELETE /api/v1/cases/{id}/analyses/{analysis_id}` |
| Messages | `POST /api/v1/analyze/message`, `POST /api/v1/analyze/email`; existing file upload accepts `.eml` and PDF |
| Intelligence | `GET /api/v1/entities/search`, `GET /api/v1/entities/{id}`, `GET /api/v1/analyses/{id}/entities`, `GET /api/v1/intelligence/graph` |
| Reports | `GET /api/v1/analyses/{id}/report.pdf`, `GET /api/v1/cases/{id}/report.pdf` |
| Privacy | `GET /api/v1/analyses/{id}/privacy`, `DELETE /api/v1/analyses/{id}/original`, `DELETE /api/v1/analyses/{id}` |
| Accounts | `POST /api/v1/auth/register`, `/login`, `/logout`, `/token`; `GET /api/v1/auth/me` |
| Jobs | `POST /api/v1/analyses/{id}/cancel`, `/retry` |
| Feedback/duplicates | `POST /api/v1/analyses/{id}/feedback`, `GET /api/v1/analyses/{id}/duplicates` |
| Operations | `GET /api/v1/admin/health`, `/users` (admin role) |

## Schema and code map

- Alembic revisions `0002`–`0006`: cases/events/assets, canonical entities/links, accounts/sessions/owners, finding feedback, job controls.
- Backend implementation: `app/models/cases.py`, `models/intelligence.py`; `services/cases.py`, `intelligence.py`, `scenarios.py`, `reports.py`, `auth.py`, `privacy.py`, `operations.py`, `feedback.py`, `jobs.py`; `analyzers/message.py`, `analyzers/qr.py`, `analyzers/url/brands.py`; existing investigation/fetch/graph integration.
- Frontend: `pages/Cases.tsx`, `Intelligence.tsx`, `Message.tsx`, `Operations.tsx`; account, context, privacy and job components. Routes: `/cases`, `/cases/:id`, `/intelligence`, `/entities/:id`, `/messages`, `/admin`.
- Extension: `browser-extension/` Manifest V3 popup and background worker. Explicit click only; current URL/link supported. Image context action remains incomplete.
- Screenshots from the passing browser flows: [case graph](screenshots/case-graph.png), [case timeline](screenshots/case-timeline.png), [entity mobile view](screenshots/entity-mobile.png), and [extension result](screenshots/browser-extension.png).

## Verification and limits

See [PRODUCT_UPGRADE_STATUS.md](PRODUCT_UPGRADE_STATUS.md) for the current pass counts and pending checks. The local URL extension flow and two-user account isolation flow passed in a browser. The local API and frontend preview were running after verification.

The rules identify potential patterns from recorded signals. Their confidence is an uncalibrated rule strength. A valid TLS certificate does not establish a trustworthy operator; an AI-generated image does not establish fraud. Large graphs and PDFs use bounded previews. Extension installation, PostgreSQL/Celery verification for the new modules, additional providers and independent fraud-rule evaluation remain outstanding.

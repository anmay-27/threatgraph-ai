# Digital Trust & Fraud Investigation upgrade

The existing FastAPI/SQLAlchemy, Celery, React and Cytoscape implementation is retained. Existing model checkpoints and detector risk policies remain authoritative. DONE requires working integration, tests and manual verification; code alone is PARTIAL.

## Architecture inspection

- Analysis records hold versioned reports; normalized evidence/asset/graph tables already exist. Reuse these rather than invent a second detector pipeline.
- Existing URL traversal validates redirects, restricts networks, limits depth/assets/bytes, and recursively investigates QR URLs. PDF QR rendering, image OCR, C2PA, scanner adapters and media inference already exist.
- Existing scenarios are limited to credential/QR phishing and malware. Extend evidence rules, never substitute fabricated outputs.
- Local development uses SQLite and a bounded thread executor. Docker uses PostgreSQL, Redis and Celery, with Alembic migrations. Existing users table is a placeholder, not authentication.
- History, registry, risk/confidence separation, dark mode, responsive layouts and JSON export are present. New features extend these pages.
- Image v3 has a local benchmark; video remains experimental and audio unavailable. Training and evaluation assets remain unchanged.

## Milestones

| Milestone | Status | Verification / remaining work |
|---|---|---|
| 1. Cases, notes, tags, grouping | DONE (local) | Additive schema, API, case pages, attach/remove, timeline, merged graph and PDF passed the latest browser flow |
| 2. Entity extraction | DONE (local) | URLs, domains, emails, phones, UPI IDs, hashes, brands, filenames and QR destinations indexed from actual reports |
| 3. Historical correlation | DONE (local) | Idempotent historical index, account-scoped occurrences, entity pages; 36 earlier records indexed |
| 4. Evidence-based fraud scenarios | PARTIAL | Recruitment/payment, credential, invoice, brand, QR and malware rules; more patterns need validated signals |
| 5. Email, message and document workflows | PARTIAL | Message and .eml, attachments, PDF text/QR, image OCR and URL recursion work; broad document authenticity needs validation |
| 6. Global graph and entity pages | DONE (local) | Search, bounded entity/analysis graph, historical links and case graph passed the latest browser flow |
| 7. PDF reports | DONE (local) | Plain-language image findings, score caveats, visual assessment panel, original preview where retained, check-by-check coverage, evidence, graph, entities, timeline, reviewer feedback, actions and appendix; Segoe/DejaVu Unicode font fallback |
| Image false-negative explanation | DONE (presentation) | A known AI-generated portrait scored 9.9% AI in the saved research model report. The UI/PDF now describe this as a possible false negative, separate score from proof, and give verification steps; model accuracy itself is not improved by wording changes |
| 8. Browser extension | PARTIAL | Manifest V3 loaded in isolated Edge; explicit benign URL submission and real result verified. Account-token flow and image context action remain |
| 9. Authentication, isolation and privacy | PARTIAL | Password hashing, sessions, roles, account isolation tests, deletion; shared-hosting review remains |
| 10. Operations | PARTIAL | Admin status, bounded retry/cancel, heartbeat timestamps; queue/worker telemetry remains |
| 11. Final polish and showcase | PARTIAL | Controlled email-PDF-QR-URL test, case browser flow, image and URL regression passed. Shared-hosting and external-data validation remain |

## Additional requested features

Implemented: feedback stored separately, duplicate/similarity lookup, local brand directory, normalized explanations, simple/technical context, case timeline, retry/cancel checkpoints. Remaining: saved searches, more external reputation adapters, complete worker telemetry, independent rule validation, non-Latin PDF font, real extension installation, optional organization mode and signed webhooks.

## Release boundary

The application remains a research prototype. Account isolation passed API tests and a two-user browser flow, but shared deployment requires a security review. Local mode defaults to single user; Docker account mode defaults on. No new field-accuracy claims are made. Do not mark the complete platform MVP-ready while milestones remain partial.

Known failure: analysis `bbc8a848-b834-4f7a-bc9e-794decd9edd4` is a user-labeled AI-made portrait that the active image detector called likely real (9.9% AI-pattern score). Stability checks remained low and out-of-domain status was not estimated. This is one documented false negative, not a measured error rate. Next model work should collect a consented, generator-diverse holdout (including portraits, editing, screenshots and recompression), measure false negatives and abstention by slice, and compare independent detectors/provenance before changing the deployed threshold. A threshold change based on this single image would not establish better accuracy.

The 19 October 2026 validation added a 1,000-image training candidate and a separate 100-image poster benchmark. The candidate failed both general and poster tests and was not deployed. The current model missed 4 of 50 AI posters in that narrow external slice and abstained on 48 of 100 posters. A live rerun of the user-supplied Google Meet URL verified the URL false-positive fix. See [IMAGE_AND_URL_VALIDATION.md](IMAGE_AND_URL_VALIDATION.md) for counts, provenance and limits.

The image page now accepts a reviewer statement about known AI origin and its basis. This is saved as feedback, displayed separately from the unchanged model score, and included in future PDF exports as unverified reviewer context. The user's statement from this conversation was recorded for the saved portrait as unverified reviewer context. Its refreshed PDF is at `storage/exports/portrait-investigation-updated.pdf`. The original upload is no longer stored and is unavailable for the latest export; the report preserves saved detector evidence and explicitly states the preview gap.

## Verification snapshot

- Backend suite: full suite passed after the PDF, Unicode, and reviewer-feedback changes.
- Frontend unit suite: 20 passed. Final production build passed.
- Browser regression: 7/7 checks passed across the latest runs. The first broad run found a missing ClamAV service and mobile overflow; corrected tests/layout passed on rerun. Case graph, PDFs, real image uploads, URL assessment, nonfacial and temporal video paths passed. Automated accessibility checks passed in those flows.
- Unpacked Manifest V3 extension loaded in isolated Edge, explicitly submitted `https://example.com/`, and displayed the actual `UNKNOWN` result and report link. This proves local-mode URL submission, not account-mode token handling or image context actions.
- Account-mode browser flow passed: a signed-in analyst created a case, signed out and revoked the bearer token; a second analyst could neither list nor open that case. A default USER account did not see analyst navigation.
- Alembic migration 0006 succeeded on an isolated SQLite copy; all 39 historical analyses in that copy were retained. PostgreSQL migration was not run this turn.
- The saved portrait PDF was generated and visually inspected locally; the live API returned HTTP 200 with an application/pdf response, and the frontend preview returned HTTP 200. The original was available in an earlier inspection but no longer present before the final export. Docker Compose was unavailable in this environment, so the latest container build remains unverified.

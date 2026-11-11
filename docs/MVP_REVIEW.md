# MVP review improvements

The existing project is extended, not rebuilt. No detector result is fabricated.

1. **Clear conclusion:** `/analysis/:id` opens with evidence, meaning, next actions, and gaps. The backend derives this summary from saved evidence, so history and JSON use the same interpretation. Original detector outputs remain intact.
2. **Image evaluation:** `scripts/evaluate_mvp_images.py` evaluates 180 additional research images with frozen publisher thresholds. SHA-256 exclusion prevents reusing images from the prior OpenFake benchmark. The manifest and predictions are saved under `research/results/mvp-image-evaluation`. Model Registry shows results and limitations. No retraining or threshold tuning was performed.
3. **URL screening:** canonical root matching handles fragments and trailing slashes. The summary distinguishes failed inspection, observed indicators, and inspection with missing coverage. Form recipient hosts are explained without claiming that cross-domain collection proves theft. Existing bounded fetching and browser restrictions remain enforced.
4. **Case explanations:** the observed attachment/QR chain is visible in simple view. Analyst view retains evidence references and missing verification. Shared entities remain correlations, not accusations.
5. **Reports:** a decision brief precedes detailed case/evidence sections. It gives findings, next steps, incomplete-check counts and conflicts. Full technical evidence follows.
6. **Readiness:** `/api/v1/readiness` checks model installation, scanner connectivity, signature freshness, PDF/QR/Office dependencies and optional OCR. Analyze, Message and Demo show actionable issues; malformed responses produce a recoverable error. These probes do not guarantee successful inference.
7. **Repeatable demo:** `/demo` includes fictional downloads and an acceptance checklist. `verify_fraud_mvp_live.py`, `verify_fraud_mvp_ui.py` and `verify_mvp_polish.py` exercise persistence, failure states, correlation, graph, report, deletion, responsive UI and new panels.

## Image results and limits

Across 90 AI and 90 genuine images: 72 AI detections, 6 AI images classified as non-AI, 12 AI abstentions; one genuine image falsely flagged. There were 32 total inconclusive results. All 30 AI posters in this sample were detected. These samples come from existing research partitions; upstream training overlap is unknown. This is not independent field accuracy. Edited-image and generator-specific validation still needs additional labeled data.

The active model is unchanged. The experiment strengthens evaluation and exposes failure rates; it does not claim an accuracy improvement from new training. AI origin stays separate from cybersecurity risk.

## Review locally

Open `http://localhost:3000/demo`. Create the previous payment case, then upload the fictional email to a new recruitment case. The email contains a real PDF and QR; the QR destination is benign example.com. Payment evidence comes from the PDF. Show actual gaps if network or scanners are unavailable. Export a fresh PDF to see the decision brief.

Readiness is operational state, so it is refreshed rather than persisted as investigation evidence. Result summaries derive from persisted evidence. Do not present dependency availability as validated detector accuracy.

## Verification completed

- Backend suite: 117 tests passed; final readiness/report regression checks passed.
- Frontend: 26 tests passed and production build succeeded.
- Real API demo: completed email/PDF/QR chain, persisted case correlation, report export and deletion.
- Browser: upload failure and success, simple/analyst views, graph, PDF download, new summary, readiness, benchmark, checklist and 390px responsive layout passed.
- PDF first page and mobile screenshot visually inspected. Artifacts: `research/results/mvp-polish` and `research/results/fraud-mvp-live`.
- Current operational limitations: stale ClamAV signatures and missing optional Tesseract OCR are surfaced in readiness. Refresh signatures before relying on malware screening.

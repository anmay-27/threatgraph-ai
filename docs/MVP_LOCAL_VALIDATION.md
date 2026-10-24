# Local MVP validation — 23 October 2026

ThreatGraph is a local investigation MVP, with working file scanning, URL inspection, image screening, evidence graphs, and JSON/PDF reports. It does not certify that a site is safe or that an image is authentic. Audio cloning detection and independently validated video deepfake detection remain outside the validated MVP scope.

## Run and check

From the repository root on this Windows installation:

```powershell
.\.venv\Scripts\python.exe scripts/start_local.py --browser
```

Open http://localhost:3000. Keep the launcher running; Ctrl+C stops services it started. The launcher uses the built frontend. After frontend changes, run `npm run build` in `frontend` before restarting. The `--browser` option enables restricted initial-page rendering for new URL investigations. Add `--update-signatures` to refresh the installed malware signature database before startup.

```powershell
.\.venv\Scripts\python.exe scripts/doctor.py --network
.\.venv\Scripts\python.exe scripts/verify_scanner.py
.\.venv\Scripts\python.exe scripts/verify_browser.py
```

On another Windows installation, first run `scripts/setup_clamav.py` and install backend requirements. Portable scanner binaries and signature databases are intentionally excluded from source control. The browser integration uses installed Microsoft Edge.

## URL investigation changes

- Accessible form labels, question headings, and ARIA references now identify requested data, including name, email, phone, and student identifiers. Field values are not retained.
- Disabled preview controls are described separately from active submission controls. A questionnaire asking for passwords or payment secrets can be flagged even when hosted on Google Forms; an ordinary Google login is not flagged merely for having a password field.
- Submitted-page observations are separated from embedded-resource redirects. SVG namespace declarations are not crawl destinations.
- Optional restricted browser observation records initial requests and rendered questions. Requests use the public-address-validated fetcher; private addresses, non-GET requests, WebSockets, downloads, and subsequent navigation are blocked. No sign-in, form submission, or user interaction occurs. This is not full browser detonation or proof about later data transfers.
- Live ClamAV checks replace the previously unavailable scanner. Clean bytes and the standard harmless EICAR test marker passed validation. Scanner health is visible through the health endpoint and upload workflow.
- The experimental URL classifier remains excluded from security-risk scoring because of observed false positives. Domain reputation is not fabricated: URLhaus remains opt-in and needs configuration; privacy mode currently disables external reputation requests.

The previously failing recruitment form was rechecked successfully. The report identifies email, name, phone, and student identifier questions, records its disabled preview controls, and no longer reports W3C as the form's redirect destination. No high-risk indicator was identified by the checks that ran; this does not authenticate the form owner.

## Reports

The UI and PDF use the same URL summary: observed facts, findings and their meaning, recommended next actions, and unresolved checks. PDFs bundle licensed fonts and wrap using actual glyph widths, including long URLs. Export with **Export PDF** or **Export JSON** on an investigation.

The saved smoke test covers desktop (1440px), mobile (390px), browser errors, extracted PDF text, and page boundaries. Artifacts: `research/results/mvp-report/validation.json`, `investigation.pdf`, and screenshots. Scanner and browser checks are recorded separately under `research/results`.

## Image model experiment

The new experiment combines 2,000 legacy samples, 1,192 deduplicated modern text-rich images, and a prior 100-poster benchmark: **3,292 total images**. The modern set covers commercial posters, infographics, receipts, tables, and UI screenshots. Its synthetic examples come from one generator, so results cannot establish universal accuracy. Source revisions, manifests, licenses, and overlap audit are retained locally.

Partitions: 1,568 training, 246 validation, 338 calibration, and 1,140 held-out evaluation images (including 200 cross-generator examples). A residual classifier head is fitted on frozen pretrained image features. Validation selects regularization; calibration selects temperature and cutoff; held-out tests decide deployment. Test outcomes must not be used to repeatedly tune the candidate.

Reproduction: `scripts/train_image_mvp.py`. Results and the deployment decision are written to `research/experiments/image-mvp-residual/metrics.json`. A candidate must improve modern balanced accuracy by at least two percentage points without losing more than two points on any other test, and meet the specified false-positive constraint. Failed candidates do not replace the installed detector.

### Completed result: candidate rejected for general deployment

| Held-out set | Images | Installed accuracy | Candidate accuracy | Installed / candidate false-positive rate |
| --- | ---: | ---: | ---: | ---: |
| Legacy image test | 600 | 98.50% | 98.83% | 1.00% / 0.33% |
| Cross-generator test | 200 | 93.00% | 90.00% | 3.00% / 1.00% |
| Modern text-rich test | 240 | 80.42% | 95.00% | 5.00% / 8.33% |
| Prior poster benchmark | 100 | 94.00% | 98.00% | 4.00% / 4.00% |

Modern AI recall improved from 65.83% to 98.33%; poster AI recall improved from 92% to 100% on these samples. However, the candidate falsely labeled 10 of 120 genuine modern images as AI, versus 6 for the installed model, and cross-generator recall fell from 89% to 81%. These regressions fail the predeclared release gate. The installed v3 model is unchanged. This is an actual completed training/evaluation result, not a claim of improved deployed accuracy. The candidate weights, fitted parameters, and predictions remain available for research. Future model changes need fresh held-out evaluation rather than tuning repeatedly against these test sets.

Backend validation: 92 tests exercised; the PDF font change required normalizing line wrapping in one text-extraction assertion, whose focused five-test report suite then passed. Frontend: 22 tests and production build passed. Live desktop/mobile/PDF checks passed, as did the scanner, restricted browser, and public network checks.

## Remaining release work

1. Independent, consented field evaluation spanning more generators, edited images, compression, and genuine human-designed posters; measure false positives and false negatives by category.
2. Configure reputation credentials if external URL lookup is wanted, with an explicit privacy choice.
3. Validate video with identity-separated genuine/manipulated clips; keep unsupported audio verdicts unavailable.
4. Before public hosting, verify account isolation, retention, abuse limits, TLS, backups, and resource limits in the target deployment. This local validation is not a public deployment review.

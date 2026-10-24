# Implementation and acceptance status

## Latest local update: 2026-10-16

- Local ClamAV daemon is running: benign stream returned OK and harmless EICAR returned a signature match. The native launcher connects on loopback. This is a signature-scan capability, not universal malware detection.
- Website/HTML collection analysis now explains sensitive field types, external destinations, HTTP and GET exposure, with a fix for unrelated forms causing credential false positives. Browser tests verified actual HTML uploads, scanner coverage and mobile accessibility.
- A pinned offline VideoMAE temporal checkpoint is installed as **experimental/unvalidated**. Actual checkpoint execution passed a clearly labelled runtime fixture; no independent real/deepfake video accuracy benchmark has been completed. Nonfacial video abstention passed a real browser upload.
- Reports now show individual capability coverage and a dedicated video explanation. Audio cloning still has no task checkpoint. Reputation stays opt-in; static HTML inspection does not observe runtime data theft.
- Current backend suite: **68 passed**. Frontend unit suite: **18 passed**. Current frontend production build passes. The older Docker/full-stack and model measurements below are historical, not a claim that the entire latest application stack was rebuilt in Docker today.
- Image v3 passed its fixed deployment gate and is installed. Official pretrained Community Forensics weights plus local calibration achieved 98.5% accuracy versus v2's 76.17% on the same fresh 600 images; missed AI images fell 94 to 6 and false positives 49 to 3. Additional comparison accuracy improved 65% to 93%. [Full results and upstream-overlap limitations](IMAGE_V3_RESULTS.md). These are local benchmark measurements, not established field accuracy.
- Earlier v2 improved 63.0% to 69.67% on its own comparison set, with a recall tradeoff. [Historical v2 measurements](IMAGE_V2_RESULTS.md). Earlier v1/v2 installation descriptions below are historical.
- Previous v2 browser verification: **6 passed** across `security-coverage.spec.ts`, `url-assessment.spec.ts` and `trained-image.spec.ts`. Actual image v2 uploads, temporal video inference, nonfacial abstention, HTML collection/scanner coverage, URL risk separation, JSON export, dark/mobile layouts and automated accessibility checks passed. These workflow tests do not establish model accuracy.
- Current v3 browser verification: **2 passed** in `trained-image.spec.ts`, covering natural/synthetic uploads, API/evaluation score parity, evidence/graph linkage, JSON export, dark/light accessibility scans and responsive mobile reports. An initial accessibility timeout cleared on the complete rerun. JSON downloads now use an attached temporary link with delayed blob URL cleanup.

## Earlier acceptance record

The repository is a working local research application. The full acceptance criteria are not yet satisfied. Unavailable models are never replaced by fabricated predictions.

| Area | Status | Evidence / remaining work |
|---|---|---|
| Monorepo, API, PostgreSQL/Redis/Celery | DONE | Latest-source Docker stack built and started; database/API healthy; Redis/Celery worker processed persisted image, audio, video and HTML investigations. |
| Input routing and persistent history | DONE | URL, image, audio, video and generic file integration tests; MIME inspection and generated filenames. |
| Secure fetch and recursive QR graph | DONE | DNS pinning, address/redirect checks, byte/depth limits; real QR multi-hop integration test. |
| Live external URL fetch | BLOCKED | Direct HTTPS smoke request to example.com timed out on this machine; protections remain enabled. |
| URL classifier training/inference | DONE | 30,000 genuine UCI records; domain-separated splits; 3 calibrated baselines; checkpoint and metrics saved. |
| URL field reliability | BLOCKED | Benign example.com/github.com spot-checks produced confident false positives. Checkpoint marked experimental; confidence capped at 0.35 pending independent-source validation. |
| Image/audio/video preprocessing and networks | DONE | Reproducible training/evaluation/inference code; CPU forward/backward and preprocessing smoke tests pass. |
| Image training and end-to-end inference | DONE (research baseline) | Two real CPU experiments, temperature calibration and local selected checkpoint. Natural/AI browser uploads verified prediction, model evidence, graph, export and dark/mobile layouts. See IMAGE_TRAINING_RESULTS.md. |
| Image field accuracy | NOT VALIDATED | Selected ConvNeXt: test accuracy 63%, F1 0.708661, false-positive rate 64%; held-out Midjourney accuracy 66%. Limited fixed-shard data and ImageNet pretraining overlap. Do not present this as a reliable general-purpose detector. |
| Audio/video trained task checkpoints | PARTIAL | Architecture/preprocessing and missing-checkpoint behavior implemented; genuine task checkpoints and evaluation still missing. |
| Metadata, hashes, QR, waveform, frame sampling | DONE | Decoder/upload tests pass. Docker includes OCR/FFmpeg; native availability is detected. |
| C2PA verification | DONE | Official signed fixture validates; byte-tampered copy reports invalid; absence is neutral. |
| ClamAV | IN PROGRESS | Scanner and optional local-daemon adapter implemented; signature-database validation remains. |
| Graph, conflicts, rule fusion, uncertainty | DONE | Same-asset/hypothesis checks, explicit conflicts, partial/INCONCLUSIVE reports and path inspection. |
| Learned fusion / research ablations | BLOCKED | Scripts implemented; independent labeled cases with out-of-fold detector predictions required for actual results. |
| Fraud inference | IN PROGRESS | Credential/connected-QR phishing and executable/signature rules. Executive impersonation and richer chain scoring remain TODO. |
| UI / accessibility | DONE | All 3 deployed-browser tests pass: upload/report/graph/history flows, unsafe-URL rejection, and automated WCAG A/AA scans on required pages and mobile submission. No automated violations detected; this does not replace a manual accessibility audit. |
| Privacy and retention | DONE | Local default, opt-in URL-only reputation, remote C2PA fetching disabled, original-file cleanup in native/Docker modes. Metadata remains sensitive. |
| Documentation / safe samples | DONE | Architecture, API, licenses, training, research, security, deployment and limitations documented. |
| Backend tests | DONE | Latest run: **42 passed**, 2 library warnings. Python lint passed. |
| Frontend tests/build | DONE | **6 tests passed**; TypeScript and production build pass after refactoring and accessibility fixes. |
| Docker latest-source verification | DONE | Latest-source rebuild passed. Real upload/worker/report/history smoke tests passed; services remain running locally. |

## Measured URL experiment

### Image-authenticity extension

The September 27 update adds light/dark themes with persistent preference, system sans-serif typography, a responsive composer, mobile history cards, keyboard workspace search and image previews. Image reports now separate the image-model suggestion from overall investigation uncertainty and explain observed evidence, failure modes and the absence of pixel-level localization. Generation-metadata inspection and three-view prediction-stability checks are implemented. The original score is preserved. Four targeted backend checks and 13 frontend tests pass, as does the production build. Real native and Docker inference completed. No improvement in measured classifier accuracy is claimed.

The pinned public image checkpoint is installed locally and real inference succeeded through the Docker worker on both a sample and the retained user image. New reports show experimental AI/non-AI suggestions, raw uncalibrated scores, provenance context and image-specific verification advice. Text-heavy/document-like inputs receive an explicit scope caution. Old reports offer a rerun action. The 11 frontend tests and 7 targeted backend workflow/adapter tests pass; the deployed image-upload browser/accessibility test passes. See `docs/IMAGE_AUTHENTICITY.md` and `research/results/image_inference_smoke.json`. No independent model-accuracy claim is made.

### URL benchmark

UCI PhiUSIIL, CC BY 4.0; deterministic 30,000-row subset. Domain-grouped counts: train 17,363, validation 6,850, test 5,787. Selected calibrated histogram gradient boosting: validation F1 0.9982608696; test F1 0.9941697258, PR-AUC 0.9977730289, ROC-AUC 0.9971346215. Test confusion matrix: TN 3,458; FP 9; FN 18; TP 2,302.

**Dataset-only scores:** external benign spot-check failures demonstrate poor generalization. See research/results/benign_spot_checks.json and docs/RESEARCH.md. The raw checkpoint outputs and original metrics are preserved.

## Open acceptance items

1. Train/evaluate real image, audio and video checkpoints on approved data; distinguish frame and video metrics.
2. Collect independent multimodal labels and run learned fusion, ablations and external OOD evaluation.
3. Validate abstention thresholds against empirical selective risk rather than conservative policy thresholds.
4. Improve URL source generalization before high-confidence field deployment.
5. Add robust multi-face tracking/alignment, executive impersonation rules and a genuine audiovisual conflict demonstration.
6. Add safe model-version-aware identical-file caching, domain age/TLS enrichment, complete history pagination and distributed quotas.
7. Authentication and tenant isolation are required before public/shared hosting; current deployment is local single-user.

## Environment

The default Windows Python alias is unusable; `.venv` uses installed Python 3.13. Native media tests reuse CPU PyTorch 2.11 through a local virtualenv `.pth` file plus torchvision 0.26. Docker has independent dependencies. Docker Desktop was started in the background. Vitest was updated to fix the initial audit issue; subsequent npm audit reported zero vulnerabilities.

Work was interrupted by an automatic-approval-review account usage limit (not an unsafe-action determination), then resumed on the user's continuation request.

## October 9 image integration verification

- Public Tiny-GenImage shards downloaded with resume and pinned SHA-256 verification; 1,800-image experiment prepared.
- EfficientNet-B0 and ConvNeXt-Tiny trained on CPU, calibrated separately, evaluated on 400 test and 200 unseen-generator examples. Selected artifact installed; exact results in IMAGE_TRAINING_RESULTS.md.
- 51 backend tests passed; 14 frontend tests passed; production build passed. The subsequent source-map-js patch leaves npm audit at zero reported vulnerabilities.
- Browser checks passed: main-page light/dark accessibility, studio interactions/mobile, and two actual trained-image uploads with evidence/model/graph/export assertions and dark/mobile screenshots. Automated checks do not establish full accessibility certification or model accuracy.
- Latest live verification uses the native SQLite/local-worker API and Vite production preview at localhost:3000. This turn did not rebuild/retest Docker/PostgreSQL/Celery; older Docker evidence above is historical.
- Original-image calibrated scores are preserved. Sensitivity diagnostics use horizontal flip and JPEG 85; confidence is heuristic. Synthetic origin is informational and cannot alone inflate security risk.
- Full-platform status remains PARTIAL: image field accuracy is inadequate, audio/video checkpoints and learned fusion remain absent, and OCR/ClamAV coverage depends on installed local tools.

Decision-boundary follow-up: added regression coverage for small transformation changes crossing the classifier cutoff, an explicit cutoff explanation, and a frozen-score abstention audit. The audit records 33 errors among 176 accepted original-image predictions; no new accuracy improvement is claimed. Existing checkpoint and measured benchmark results remain unchanged.
Follow-up verification: 5 targeted inference tests, 15 frontend tests, production build, and 2 real-upload browser tests passed. Browser tests include threshold-crossing assertions, dark/mobile accessibility checks, graph linkage and export. Native API was restarted with the fix; frontend remains at localhost:3000.

## URL screening signal policy

Experimental URL classifier scores no longer contribute to overall security risk, regardless of how high or low the model output is. They remain in evidence, model results and exported JSON, with informational graph severity. Independent scored findings (for example a credential destination mismatch) still contribute normally. With only a model score and failed fetch, risk is UNKNOWN/INCONCLUSIVE, not MODERATE and not SAFE.

URL reports now list failed checks and their recorded reasons directly, explain model limitations and provide a new-check action. Historical reports remain immutable and are explicitly identified as using an older scoring policy. No domain allowlist or special LeetCode exception was introduced. This is an evidence-policy correction, not improved classifier accuracy; external-data validation/retraining remains needed.

Verification: 9 targeted backend tests, 15 frontend tests, production build and live LeetCode browser submission passed. See research/results/url-risk-smoke.json and docs/screenshots/url-assessment.png.

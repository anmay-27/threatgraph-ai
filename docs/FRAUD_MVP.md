# ThreatGraph AI: focused digital-fraud investigation MVP

This is an additive upgrade of the existing React/FastAPI application. No reference repository was imported or used as a replacement backend. Audio/video remain existing experimental modules and are not part of the primary demo or this acceptance claim.

## Architecture references

- [OpenCTI](https://github.com/OpenCTI-Platform/opencti): entity/relationship representation and traceable intelligence observations.
- [IntelOwl](https://github.com/intelowlproject/IntelOwl): modular analysis jobs with explicit analyzer availability and results.
- [TheHive](https://github.com/TheHive-Project): cases, linked observables, investigator notes and timelines.
- [Cortex Analyzers](https://github.com/TheHive-Project/Cortex-Analyzers): separate analyzer outputs and failure handling.
- [Multimodal Deepfake Detection](https://github.com/yagmurtncr/multimodal-deepfake-detection): modality-specific evidence before combining results; no new audio/video development.
- [Content Authenticity Initiative](https://github.com/contentauth): provenance verification as a separate evidence source, not inference from missing metadata.

## What changed

Case pages now have a simple/analyst assessment with direct file upload, automatic refresh while analyses run, fraud hypotheses, evidence references, observed asset paths, linked cases, coverage gaps, conflicts, separate synthetic-media findings, and recommended actions. Upload/link failures are visible; if linking fails, the independent investigation remains recoverable through History.

Fraud-chain rules can connect recruitment language to an advance-fee request through an actual directed email/attachment/QR/URL path. Unrelated findings cannot be joined merely because they occur in one report. These are hypotheses with missing evidence and actions, not criminal determinations.

Fetched page text and declared UPI links now feed the evidence and entity pipelines without submitting forms or automatically following every anchor. Explicitly labelled UPI handles and payment graph nodes enter the persisted entity index. Cases correlate accessible shared payment, contact, URL, domain and file-hash entities. Shared infrastructure does not increase risk or establish a shared attacker. Correlation links appear in the case graph and PDF.

The case assessment is computed from persisted analyses and entity links on each read. Deletion/detachment therefore removes stale correlations without rewriting saved detector reports. Case deletion preserves independently stored analyses, as explicitly described in the UI; analysis deletion removes its original, findings and entity links.

## Primary demo

Open `/demo` for downloadable, explicitly fictional inputs:

1. Create a previous case and upload `previous-payment.txt`.
2. Create a recruitment case and upload `fictional-offer.eml`.
3. The actual pipeline extracts sender/domain, parses the PDF attachment, decodes the QR and attempts its URL, extracts the PDF's invented payment identifier, finds the previous case, and infers an advance-fee recruitment hypothesis.
4. Switch between simple and analyst views, inspect the threat graph, and export the case PDF.

The public demo QR points to **benign example.com**. Payment information comes from the fictional PDF; we do not pretend it was extracted from a malicious live page. The exact email → PDF → QR → payment webpage → UPI → previous-case chain is tested with an explicitly controlled network response in `test_fraud_mvp.py`. Fixtures are input material, never precomputed detector outputs. URL-fetch failures remain visible as partial coverage.

## Validation evidence

- Backend workflow tests cover the exact controlled page chain, persistence, cross-case payment correlation, graph linkage, PDF text and removal of a deleted related case.
- A negative test rejects fraud-chain inference for disconnected clues.
- Existing backend tests cover URL safety, recursion, provenance, media/security risk separation, documents, message parsing, case ownership, history, cancellation, retention and deletion.
- Frontend tests cover both case views and preserve separation of synthetic origin from cybersecurity risk.
- Live API verification uses fictional email/PDF inputs, the real benign URL, persistent cases, PDF extraction and disposable source/analysis/case deletion. Output: `research/results/fraud-mvp-live/verification.json`.
- Live browser verification checks desktop/mobile layout, analyst mode, graph tab and actual downloads. Screenshots and results: `research/results/fraud-mvp-live/`.

Run `scripts/make_fraud_demo.py` to regenerate sample inputs; `scripts/verify_fraud_mvp_live.py` creates two retained demonstration cases and cleans up a disposable deletion test; `scripts/verify_fraud_mvp_ui.py` checks the saved demo case in Edge. These checks do not establish production-scale reliability or detector field accuracy.

## Remaining limits

Cases correlate exact normalized identifiers, not proven actor identity. Fraud hypotheses are bounded deterministic rules. C2PA verification, malware scanning, URL reputation and browser inspection retain their actual availability states. No detector output is invented. The current OpenFake image weights are noncommercial research weights; activation is experimental. Synthetic-media findings alone are excluded from cybersecurity risk. Large-scale deployment, independent detection evaluation and licensing review remain outside this local MVP verification.

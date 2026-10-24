# Security capability changes — 2026-10-16

Reports now expose separate check coverage for AI images, visual deepfakes, synthetic voice, malware signatures, phishing, declared data collection, file structure and signed provenance. A completed check means it ran, not that the content is safe. Older persisted reports retain their original evidence; rerun retained content or submit it again for new checks.

## Malware

The local ClamAV container was started and the native launcher now defaults to `CLAMAV_HOST=127.0.0.1`. Compose exposes port 3310 only on loopback. Start it with `docker compose --profile clamav up -d clamav`; Docker Desktop must be running. The API sends uploaded/downloaded bytes to the local daemon using INSTREAM.

Verified engine response: `ClamAV 1.5.4/28150/Sun Oct 11 06:26:01 2026`. A benign stream returned `OK`; the harmless standard EICAR test string returned `Eicar-Test-Signature FOUND`. This demonstrates real signature scanning, not detection of all malware. Signature freshness was not independently established beyond the reported version/date. Scanner failure remains visible rather than becoming a clean result.

## Websites and HTML uploads

Static inspection inventories requested field types, form destinations/methods, third-party script references, and inline references to location, camera/microphone, clipboard and beacon APIs. Findings explain cross-domain sensitive submissions, unencrypted HTTP collection and secrets submitted through GET. Input values are never copied into this inventory. Form ownership, base URLs and submit-button overrides are considered; dialog forms are not treated as network submissions.

A false-positive bug was fixed: an unrelated newsletter form can no longer be paired with a password elsewhere on a page to invent credential exfiltration. Legitimate outsourced login/payment forms can still need review; cross-domain submission is not proof of theft.

JavaScript is not executed, external script bodies are not inspected, and actual outbound data, consent and runtime behavior are not observed. Page fetches remain bounded and protected against SSRF. Reputation remains opt-in and requires configuration; private browsing mode does not query external reputation services. The experimental lexical URL classifier remains excluded from numeric security risk due to observed false positives.

## Media

See [video screening](VIDEO_SCREENING.md) and the preregistered [image v2 protocol](IMAGE_V2_PROTOCOL.md). AI origin is separate from malicious intent. Missing audio models or unavailable provenance verification remain explicit.

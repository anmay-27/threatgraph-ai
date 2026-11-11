# Media readiness — 10 November 2026

## Verified in this review

- Document/video/media/limit test selection passed (12 tests).
- Document and new media-bound regression selection passed (8 tests; overlaps the selection above).
- Real installed VideoMAE checkpoint executed successfully on a four-second translated still-image fixture, sampling 16 frames. This is a runtime check, NOT a labelled accuracy benchmark. Result saved in research/results/video-runtime-smoke.json.
- Audio now reads bounded blocks, preserves opposite-phase stereo peaks, and rejects empty/non-finite input. Video QR inspection samples at most 24 positions including the final frame. PDF extraction no longer materializes all page objects before applying its limit.

## Remaining gaps

- Audio has no registered trained checkpoint. Waveform/metadata inspection is not voice-clone detection; no audio accuracy claim is justified.
- Video is experimental and uncalibrated, targets facial videos, samples only 16 model frames and has no independent accuracy evaluation. It does not verify an entire video or its soundtrack.
- Neither FFmpeg nor Tesseract was found on PATH in this review. Video audio extraction and scanned-PDF OCR therefore remain unavailable in this environment.
- Document checks cover PDF text/links/QR and Office text/macros/external-resource declarations. They do not establish factual truth or authenticity. Embedded files are flagged, not fully inspected. PDF text is limited to 30 pages, QR to 10, optional OCR to 5.
- This review did not reverify all modalities through the authenticated browser upload/report flow. Old upload verification scripts need account-aware sessions before use.

## Before claiming production readiness

1. Configure Google OAuth credentials locally if Google login is desired; follow GOOGLE_LOGIN.md. Existing password login does not require them.
2. Install/configure FFmpeg and Tesseract, then verify real audio-track extraction and scanned-PDF text using known fixtures.
3. Select a licensed pretrained audio anti-spoofing checkpoint and implement its exact preprocessing and supported-format handling. Evaluate before exposing authenticity claims.
4. Evaluate video/audio on labelled held-out real/fake data separated by source, speaker/person and generator. Include compressed files, unseen generators and no-face/non-speech input; report false positives, false negatives and abstentions separately. Do not train on the test partition.
5. Run authenticated browser uploads, saved-history retrieval and PDF exports for each supported format and failure case.
6. Before public hosting: HTTPS/secure cookies, durable database/uploads, backups, secret configuration and model licensing review. No deployment was performed.

# ThreatGraph AI — presentation guide

## Start before the presentation

Run from the project directory:

```powershell
.\.venv\Scripts\python.exe scripts/start_local.py --browser
```

Open http://localhost:3000/demo. Check API, image model, and malware scanner status. Keep the launcher open. If internet access is unreliable, use the fictional message sample, a local image, and a previously completed report. New URL checks require network access.

## Three-minute walkthrough

1. **Problem (30 seconds):** A suspicious link, image, or message can contain several kinds of evidence. A single AI score cannot establish whether content is malicious.
2. **Run an investigation (60 seconds):** Open Demo guide, copy the clearly fictional recruitment message, and submit it through Message analysis. Explain the observed fee and urgency indicators. Rules are screening signals, not proof of criminal intent.
3. **Explain the evidence (45 seconds):** Inspect a graph node and the individual findings. Show which checks ran and which did not. For an image, distinguish the model's origin suggestion from security risk.
4. **Deliver the result (30 seconds):** Export PDF for a readable report and JSON for structured technical review.
5. **Limits and next steps (15 seconds):** Independent model evaluation, broader generator coverage, and externally configured URL reputation remain work to do.

## Claims supported by the implementation

- URL fetching validates public addresses and redirects; optional restricted rendering inspects initial requests and questions.
- ClamAV checks uploaded/downloaded bytes when the local daemon and signatures are ready.
- Image analysis combines a pretrained research classifier, local calibration, transform stability checks, metadata, and available provenance.
- Reports preserve evidence and state incomplete coverage explicitly.
- The latest 3,292-image experiment improved some benchmarks but failed its general release gate. Do not describe that candidate as the deployed model.

## Avoid these claims

Do not promise perfect AI detection, verified identity, complete data-theft detection, universal malware coverage, production deployment, or validated audio deepfake detection. Video screening is experimental. No new measured accuracy claim was made during the UI polish.

## Evidence for submission

The source repository is https://github.com/anmay-27/threatgraph-ai. It excludes uploaded content, private reports, datasets, credentials, and large model weights. Local setup and model preparation are necessary on another computer; cloning alone does not copy the installed detectors.

Run `scripts/verify_submission.py` with the local app open to exercise both themes, mobile/desktop layouts, a real message analysis, and PDF export. Local artifacts are saved to `research/results/submission/` and excluded from GitHub.

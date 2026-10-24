# Image authenticity suggestions

Image reports now lead with an explicit AI-generation assessment, separate from the overall threat score. A high synthetic-media score does not establish malicious intent; a low score cannot authenticate a certificate, person, event or document.

## Current project-trained model

The selected local registry now uses ConvNeXt-Tiny, trained and measured by this project. See [actual results](IMAGE_TRAINING_RESULTS.md) and [reproduction commands](ML_PIPELINE.md). The frontend displays the original calibrated AI probability, threshold-derived class suggestion, heuristic confidence, uncertainty, architecture/version, preview and measured subset metrics. It abstains on high uncertainty, unfamiliar embeddings or unstable transformation scores. Calibration is dataset-specific and test accuracy is only 63%; no high-accuracy claim is justified.

Natural and synthetic image uploads were verified through the browser, report, evidence/models, graph and JSON export. AI origin alone is excluded from security-risk scoring. Missing security/OCR coverage can still produce PARTIAL reports while the image detector works.

## External pretrained fallback (historical reports)

Install dependencies from `ml/requirements.txt`, then run `python scripts/install_image_model.py`. Recreate Docker services after changes to runtime dependencies. Model files mount from `models/image` and are ignored by Git.

The installer pins [Ateeqq/ai-vs-human-image-detector](https://huggingface.co/Ateeqq/ai-vs-human-image-detector/tree/60e82406916921b823616bee33397baab38af3f0), revision `60e82406916921b823616bee33397baab38af3f0`, under the publisher's Apache-2.0 license. It records the downloaded safetensors SHA-256 and preserves the publisher's model card. Attribution: Ateeqq, AI and Human Image Classification Model. The adapter uses the published processor and AI/human label mapping. Inference is local-only, uses safetensors, disables remote code, and never sends an uploaded image to Hugging Face.

This is an externally pretrained SigLIP classifier, not a model trained or independently evaluated by this project. The publisher reports overfitting. Publisher benchmark accuracy is not reproduced or presented as local performance. There is no calibrated field probability or validated OOD detector for this checkpoint. Evidence confidence is capped at 0.35.

## External-model display policy

- AI softmax score at least 0.8: **Model suggests: likely AI-generated**.
- AI softmax score at most 0.2: **Model suggests: likely non-AI**.
- Between these bounds: **Uncertain**.
- No model output or OOD detected by a supported detector: **Unable to determine**.
- Contradictory signed origin claims and model output: **Conflicting signals**.
- OCR identifies document-related terms or at least 80 words: **Document-like image — AI origin remains uncertain**, while preserving the raw model suggestion. This text heuristic is a scope caution, not a document classifier.

These cutoffs are conservative UI policy, not measured operating points. The raw score is labeled uncalibrated. Signed generation/camera declarations are shown as claims, not proof of scene truth. Missing EXIF/C2PA is neutral. Assessment only uses the submitted image's evidence, not linked assets. No visual localization or artifact explanation is fabricated.

For certificates, screenshots and mixed designs, verify the original and issuer separately. A single whole-image classifier cannot establish which regions were generated or edited.

Existing reports retain their original evidence. Use **Run image detector again** to create a new investigation from the retained local original; if retention has removed it, upload the image again. JSON export includes the displayed image assessment.

## Evidence and prediction stability

The image inspector now recognizes explicit PNG generation parameters, diffusion sampling workflow nodes and selected EXIF generation-tool identifiers. These editable fields are reported as unverified metadata, never as signed provenance or definitive proof. Plain mentions of AI and ordinary editing-software tags do not qualify.

The local SigLIP adapter preserves the original score and additionally evaluates a horizontal flip and JPEG quality-85 copy. A score range of at least 0.25 triggers an instability warning and lowers evidence confidence. The three views are correlated checks from the same model, not independent votes. Stable scores can still be wrong; this is not a measured accuracy improvement. No visual defect localization, heatmap or causal explanation is claimed.

Reports distinguish observations, classifier output, scope limitations and verification actions. Rerun existing images to obtain these new checks. A labeled external benchmark, including user-reported failures and genuine negatives, is still necessary before improving or claiming field accuracy.

## Decision-boundary sensitivity follow-up

Trained-image inference now treats a class change under horizontal flip/JPEG 85 as instability even when the score range is below 25 percentage points. The original calibrated probability and raw class are preserved, while the verdict abstains. Reports show the calibration-selected class cutoff and distinguish threshold crossing from a large score spread. Inconclusive/OOD/unstable classifier outputs no longer count as corroboration of signed provenance in the UI.

The frozen original-score-only abstention audit (`python scripts/audit_image_abstention.py`) accepts 176/400 examples (44% coverage), with 33 errors among accepted outputs (18.75%). This excludes OOD, transformations, provenance and document cautions, so it is not full deployed-policy accuracy. No test-label threshold tuning or weight changes were made. The result reinforces that heuristic confidence is not correctness probability.

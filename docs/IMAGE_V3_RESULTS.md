# Image v3: measured upgrade

The installed detector is now `image-detector-v3-community-forensics`, using the official [OwensLab Community Forensics checkpoint](https://huggingface.co/OwensLab/commfor-model-384). The vision weights were trained upstream; this project fitted a scalar temperature and decision cutoff on a separate local calibration partition. It did not train the underlying ViT from scratch.

## Same-image comparison

Fresh final test: **600 images**, balanced between 300 real and 300 synthetic. Both the unchanged installed v2 pipeline and candidate were evaluated on exactly these images. The [protocol and replacement criteria](IMAGE_V3_PROTOCOL.md) were fixed before candidate predictions.

| Measurement | Previous v2 | Installed v3 |
|---|---:|---:|
| Accuracy / balanced accuracy | 76.17% | **98.50%** |
| Correct classifications | 457 / 600 | **591 / 600** |
| AI-image recall | 68.67% | **98.00%** |
| Missed AI images | 94 / 300 | **6 / 300** |
| Real images falsely flagged as AI | 49 / 300 | **3 / 300** |
| False-positive rate | 16.33% | **1.00%** |
| Precision | 80.78% | **98.99%** |
| F1 | 0.7423 | **0.9849** |
| ROC-AUC | 0.8473 | **0.9989** |
| Brier score | 0.1593 | **0.0206** |
| Expected calibration error | **0.0281** | 0.0304 |

Paired accuracy improvement: **22.33 percentage points**. A 2,000-repetition, class-stratified paired bootstrap gave a 95% image-level interval of **19.00 to 25.83 points** on this dataset. This interval does not quantify uncertainty across future generators or real-world sources.

The previous 69.67% v2 result used a different test partition. Comparing 76.17% with 98.50% here is the valid same-image comparison. This compares complete pipelines including their calibration, not a controlled architecture-only experiment.

An additional 200-image partition (100 Midjourney, 100 separate real images) improved from **65% to 93% accuracy**; v3 missed 11 synthetic images and falsely flagged 3 real images. Midjourney was excluded from this project's local calibration, but cannot be claimed unseen by the upstream pretrained model. Calibration error on this partition was 0.1325, so probability reliability remains imperfect even with good class accuracy.

## Reproducibility and integrity

- Model revision: `6076002bf0d9dd37537f965ee2f06f826c333b61`; safetensors SHA-256 `b89f36275f3bf5e2b040eee36597a8f19db051bff9a473a9cf7b2466284fb387`.
- Official implementation inspected at commit `ee5b71d43db0f3779e1edd64ee927b13f2dd6ad4`. Local adapter uses strict weight loading, pinned timm 1.0.15, shorter-edge resize 440, center crop 384 and ImageNet normalization. No downloaded repository code executes.
- The local implementation reproduced the upstream example's rounded raw score: 0.9988338 versus published 0.9988. This checks numerical implementation, not accuracy. Audit: `research/results/community-model-parity.json`.
- Dataset: pinned Tiny-GenImage train shards 5, 8 and 10; fresh validation shard 3. Excluded all v1/v2 manifest identities, decoded hashes and near-duplicate perceptual hashes. Removed 2,800 previously selected identities and one near duplicate; separate manifest checks found zero prior identity/pixel overlap and verified all 2,000 saved image contents.
- Partitions: 400 reserved unused training images, 400 diagnostic validation, 400 calibration, 600 final test, 200 additional comparison. Seed 42.
- Calibration temperature: **2.5198420998**. Decision threshold: **0.18**, selected using calibration balanced accuracy with an empirical FPR ceiling of 20%. Parameters were saved before final test predictions. The cutoff is a model operating point, not a universal 50% rule.
- Full metrics, per-generator breakdown, predictions and plots: `research/experiments/image-community-v3/`. Previous registry: `models/image/registry-before-v3.json`. Previous v2 checkpoint is retained.

## Application verification

The installed v3 detector passed both real-browser upload tests (natural and synthetic). API scores matched the saved evaluation probabilities to five decimal places. Evidence, graph linkage, JSON export, dark/light accessibility scans and mobile layout checks passed. The JSON download now attaches its temporary link to the document and delays blob URL revocation. An earlier accessibility scan timed out; the final complete rerun passed both tests in one minute. Backend tests: 68 passed; frontend unit tests: 18 passed; production build passed. These workflow checks do not establish accuracy beyond the benchmark above.

## Remaining limitations

**98.5% is a local benchmark result, not established real-world accuracy.** Upstream training/pretraining overlap with GenImage/ImageNet cannot be excluded. The small fixed-shard sample does not represent all current generators, screenshots, edited images, certificates or mixed real/AI content. The measured class accuracy is separate from the application's uncertainty/abstention policy.

The detector preserves original scores and checks flip/JPEG sensitivity. It does not locate altered pixels and has no validated out-of-domain detector. AI generation alone does not establish malicious intent. Video and URL accuracy were not improved or revalidated by this image experiment.

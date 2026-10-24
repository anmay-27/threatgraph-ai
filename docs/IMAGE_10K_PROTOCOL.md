# Image 10k experiment — protocol fixed before evaluation

Requested outcome: train using at least 10,000 images, then compare against the installed model. A prepared pipeline or dataset download is not completed training.

## Data and partitions

- Pinned source: `TheKernel01/Tiny-GenImage`, revision `89c4fe9efd0ebc7ce5c7641ef57d578ccd639c69`.
- Training shards: 1, 2, 3, 4, 6, 7, 9, 11, 12, 13; validation-source shard: 1. Downloads must match published SHA-256 checksums.
- Fresh GenImage partitions: 10,000 training, 1,000 validation, 1,000 calibration, 1,000 test, 200 held-out-generator examples. Midjourney synthetic examples do not enter fitting.
- Existing modern text-rich development examples add 568 training, 146 validation, and 238 calibration examples; its 240 test images and earlier 100-poster benchmark stay outside fitting.
- Expected training count: **10,568**, subject to preparation succeeding. If insufficient unique examples remain, preparation fails instead of duplicating examples to reach the count.
- Prior manifests are excluded by source identity, decoded-pixel SHA-256, and perceptual hash Hamming distance <=4. Global deduplication precedes split assignment. Semantic similarity and upstream pretraining overlap remain possible.

The dataset mirror declares CC-BY-NC-SA-4.0; underlying rights remain with their owners. This experiment is research use, not commercial deployment clearance. Modern text-rich synthetic samples represent one generator. No dataset images or model binaries are pushed to GitHub.

## Training and release decision

Use the frozen pretrained Community Forensics encoder and train a regularized residual classifier head. Encoder weights are not retrained from scratch. Validation selects regularization; calibration selects temperature and threshold. Tests are not used to tune parameters.

Release gate remains: modern balanced accuracy improves at least two points, no evaluated group loses more than two points, and false-positive rates do not exceed max(5%, installed baseline). Passing this gate only makes a candidate eligible for additional transformation-stability validation. The pipeline never automatically changes the installed model.

Run `scripts/run_image_10k.py` to resume download, preparation, feature extraction, training and evaluation. Status: `research/experiments/image-10k/run-status.json`. Final metrics: `research/experiments/image-10k/metrics.json`. Cached feature batches allow interrupted extraction to resume.

## URL review in the same update

Disabled fieldsets and their first-legend exception are now interpreted correctly, including alternate form submission buttons. Gzip/deflate responses are decoded with separate transferred-byte and expanded-byte limits. Truncated streams and expansion bombs are rejected; public-address and redirect controls remain intact.

Live checks inspected example.com and Google Meet's sign-in redirect without high-risk page findings. Wikipedia returned HTTP 403 and was recorded as unassessed. Controlled offline external-secret and hosted-secret forms produced the expected findings. These spot checks are not a population-level phishing accuracy benchmark. The experimental URL model remains excluded from security scoring.

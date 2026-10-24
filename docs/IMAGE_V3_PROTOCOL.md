# Image v3 evaluation protocol — fixed before candidate predictions

2026-10-16. The goal is higher image accuracy without the v2 recall/false-positive tradeoff.

- Candidate: official OwensLab/commfor-model-384, revision `6076002bf0d9dd37537f965ee2f06f826c333b61`, frozen pretrained weights. Architecture and preprocessing must match the official implementation; no downloaded Python execution or non-strict checkpoint loading.
- New comparison data: Tiny-GenImage revision `89c4fe9efd0ebc7ce5c7641ef57d578ccd639c69`, fresh source validation shard 3 for final test. Source train shards 5, 8 and 10 provide unused calibration/validation samples. Exclude every v1/v2 manifest identity, decoded-pixel hash and near-duplicate pHash. Shard 8 was added before candidate predictions because the initial deduplicated pool had too few unused synthetic images; no old test examples are recycled.
- Balanced partitions: 400 reserved train (unused), 400 validation (diagnostic only), 400 calibration, 600 test, 200 Midjourney comparison. Seed 42. Do not reuse v1/v2 final test data for tuning. Midjourney is unseen by this project's calibration, but cannot be claimed unseen by the externally pretrained checkpoint.
- Train only a scalar temperature on calibration scores by minimum Brier loss over 25 log-spaced values from .25 to 4. Select threshold using calibration balanced accuracy subject to empirical FPR <=20%; ties prefer higher recall then higher threshold. No fitting of vision weights in this experiment.
- Evaluate installed v2 unchanged and the calibrated candidate on the same fresh test and Midjourney partitions. Deploy only if candidate balanced accuracy improves by at least 2 percentage points, recall is no lower and FPR no higher than v2 on the fresh test. Also require no lower balanced accuracy on the Midjourney comparison. Otherwise retain v2. This gate does not permit retuning on test labels.
- Record full confusion matrices, per-generator metrics, raw predictions and calibration metadata. Report a paired bootstrap interval for accuracy difference; do not manufacture certainty from a small sample.
- Original-photo classification is measured separately from deployment abstention/stability behavior. Third-party training/pretraining overlap with GenImage/ImageNet cannot be excluded; this is a local comparative benchmark, not independent field accuracy. No claims about video or URL accuracy follow from this image experiment.

Sources: https://huggingface.co/OwensLab/commfor-model-384 and https://github.com/JeongsooP/Community-Forensics .

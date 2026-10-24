# Image v2 experiment protocol (fixed before evaluation)

Date: 2026-10-16. Existing v1 test data will not be used for new tuning.

- Data: pinned Tiny-GenImage train shards 5 and 10; fresh validation shard 2. Exclude all v1 manifest source names, decoded hashes and near-duplicate perceptual hashes. Retain Midjourney as an unseen generator.
- Planned balanced partitions: 2,000 train, 400 validation, 400 calibration, 600 test, 200 OOD (subject to available deduplicated samples).
- Model: ImageNet EfficientNet-B0, last two feature blocks trainable, 6 epochs, AdamW learning rate 0.0003, batch 16, seed 42, CPU 4 threads, patience 3. Select epoch by validation ROC-AUC.
- Calibration: temperature fit on calibration only. Threshold maximizes calibration recall subject to empirical calibration false-positive rate <=10%, tie-breaking by balanced accuracy then higher threshold. This is an empirical operating point, not a population error guarantee.
- Save metrics on fresh test/OOD once. Evaluate the unchanged installed v1 checkpoint on the same fresh test partition. Install v2 only if its test balanced accuracy exceeds v1 on that partition and its FPR is below 25%; otherwise preserve the current registry and document failure. A deployment gate is not parameter tuning. Neither checkpoint nor threshold may be tuned after reading test results.
- No manipulation of scores, model confidence or example selection to manufacture a successful demonstration. Video deepfake and synthetic voice need separate task-specific validated checkpoints.

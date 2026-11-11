# Additional diversity experiment

Run `scripts/run_image_diversity.py`. Logs are in `storage/logs/image-diversity.log` and `image-diversity-errors.log`.

Use unused samples from the already downloaded, pinned GenImage shards. Exclude all existing prepared/external manifests by source identity, decoded pixel hash, and perceptual-hash distance <=4. Keep previous partitions unchanged. The new partitions target 2,000 training, 400 validation, 400 calibration, and 500 test images, balanced by real/synthetic class. Synthetic sampling rotates across all eight available generators, including Midjourney. The resulting total training count should be 12,568; preparation fails if unique samples are insufficient.

The unchanged balanced-head procedure gives each source/class stratum equal fitting weight. Validation selects among three regularization strengths using worst-source log loss; calibration selects temperature and a cutoff subject to each source's empirical false-positive rate <=2.5%. Existing feature caches are reused after fingerprint verification; only new batches require encoder inference. Encoder parameters remain frozen.

Old test sets are regression checks. Midjourney is no longer an unseen training generator, so the old `legacy_ood` result must not be described as out-of-distribution performance. `fresh_holdout` contains the newly reserved 500 examples, never fitted or used for selection. It remains from the same dataset mirror, with possible unknown upstream pretraining overlap; it is not independent field validation or a test of new generator families.

The experiment never installs a candidate automatically. Check false positives, detection recall, fresh holdout results, and transformation stability before proposing installation. No commercial rights or new real-world accuracy claims follow from these research results. Do not tune against the fresh holdout after opening it.

Preparation adjustment before training or evaluation: deduplication left only 275 eligible real validation-source images. Reserve 250 per class (500 total), rather than the planned 300 per class. Training, validation and calibration counts are unchanged. This adjustment uses availability only, not model outcomes.

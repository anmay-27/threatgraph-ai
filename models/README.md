# Local model registry

Training writes `models/{url,image,audio,video,fusion}/registry.json` and a checkpoint. The API reads this metadata; workers cache loaded checkpoints by path and modification time. Only install trusted local checkpoints: joblib files can execute code.

No checkpoint means **unavailable**, never a fabricated probability. `image/registry.json` is the authoritative active selection. Project-trained v1/v2 checkpoints and measurements are retained; see [v1 results](../docs/IMAGE_TRAINING_RESULTS.md), [v2 results](../docs/IMAGE_V2_RESULTS.md) and the [v3 comparison protocol](../docs/IMAGE_V3_PROTOCOL.md). Installation does not imply production readiness.

Reproduce with [ML pipeline](../docs/ML_PIPELINE.md), then `scripts/install_trained_image.py`. The installer selects validation ROC-AUC and preserves the previous registry as `image/registry-before-project-training.json`. The external SigLIP files are retained for rollback; `scripts/install_image_model.py` refuses to replace the project-trained registry unless `--replace` is explicit. Do not ensemble these models without new validation.

Model binaries are ignored by Git. Mount models read-only in deployment. Registry fields include name, version, architecture, dataset/revision, training date, measured metrics, calibration/temperature, threshold, checkpoint path and SHA-256. Research data mirror declares CC-BY-NC-SA-4.0; underlying source image rights remain.

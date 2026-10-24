# Image v2: measured replacement, 2026-10-16

EfficientNet-B0 v2 is installed at `models/image/project-trained-v2.pt`. It passed the deployment gate fixed in [the protocol](IMAGE_V2_PROTOCOL.md): higher balanced accuracy than the unchanged v1 on the identical fresh test set, and false-positive rate below 25%. This is a bounded research improvement, not validated general-purpose detection.

## Same-test comparison

Fresh test: 600 images, 300 real and 300 synthetic. No weights, temperature or threshold were fitted on this test partition.

| Metric | Previous ConvNeXt v1 | EfficientNet v2 |
|---|---:|---:|
| Accuracy / balanced accuracy | 63.00% | 69.67% |
| Real-image false-positive rate | 56.00% | 22.67% |
| AI-image recall | 82.00% | 62.00% |
| Precision | 59.42% | 73.23% |
| F1 | 0.6891 | 0.6715 |
| ROC-AUC | 0.7394 | 0.7713 |
| Brier score | 0.2186 | 0.1993 |

V2 confusion matrix: 232 true negatives, 68 false positives, 114 false negatives and 186 true positives. Fewer false accusations come at the cost of missing more AI images. The improved accuracy does **not** mean every metric improved. These numbers measure original-image class predictions; they are not the accuracy of the UI's abstention/stability policy.

Unseen-generator partition: 100 Midjourney and 100 separate real images. V2 accuracy 64.5%, AI recall 47%, FPR 18%, ROC-AUC 0.7109; unchanged v1 accuracy on the same partition was 56.5%. More than half of these unseen-generator AI images were missed. Embedding OOD flagged only 0.5% of this partition, so its gate cannot be relied on to identify unseen generators.

## Training and calibration

Pinned Tiny-GenImage train shards 5 and 10, validation shard 2; prior v1 source identities, pixel hashes and near-duplicate hashes excluded. Balanced partitions: 2,000 train, 400 validation, 400 calibration, 600 test, 200 unseen-generator test. Midjourney excluded from training, validation and calibration. SD14 is absent in the selected shards.

Six CPU epochs, last two feature blocks unfrozen, learning rate 0.0003, batch 16, seed 42. Epoch 6 selected by validation ROC-AUC 0.8709. Temperature 2.2449240966 fitted on calibration; threshold 0.59 selected for maximum calibration recall subject to empirical FPR <=10%. Actual calibration FPR was 9%, but fresh-test FPR was 22.67%: the calibration target is not a field guarantee.

Training history, split manifest, metrics, per-generator results, predictions and plots are in `research/experiments/image-efficientnet-v2/`. The unchanged baseline evaluation is in `research/experiments/image-v1-on-v2/`. `research/results/image-v2-deployment-gate.json` records the comparison. Previous checkpoint and registry are retained for review/rollback.

The source is a small fixed-shard GenImage derivative with possible semantic/pretraining overlap, not a representative sample of contemporary generators, screenshots, certificates, edited photos or artwork. The UI retains raw scores, prediction stability and inconclusive results instead of claiming guaranteed authenticity.

## Browser verification

The fixed first real and synthetic entries in the fresh test manifest were uploaded through the browser using the installed v2 registry. Both completed model inference; evidence, JSON export, stability diagnostics, dark/light themes, mobile layout and automated accessibility checks passed. This verifies application wiring rather than class accuracy. Reports are recorded in `research/results/image-upload-natural.json` and `image-upload-synthetic.json`.

# Project-trained image detector: measured results

This is a bounded CPU transfer-learning experiment, not a claim of production accuracy. Both candidates use frozen ImageNet encoders and trained binary heads. No Swin experiment was run because CUDA is unavailable.

## Dataset and protocol

[Tiny-GenImage](https://huggingface.co/datasets/TheKernel01/Tiny-GenImage), pinned revision `89c4fe9efd0ebc7ce5c7641ef57d578ccd639c69`. Two SHA-256-verified shards. Original benchmark: [GenImage](https://github.com/GenImage-Dataset/GenImage). Mirror declares CC-BY-NC-SA-4.0; underlying image rights remain with owners.

Balanced partitions: train 800, model-selection validation 200, calibration 200, test 400, unseen-generator test 200 (100 Midjourney + 100 separate real images). Seed 42. Midjourney is excluded from fitting, model selection and calibration. Test/OOD use only the source validation partition. Global filename, decoded-pixel hash and pHash checks found no duplicates. Source prompt/scene family identifiers are unavailable, so semantic leakage cannot be ruled out. Fixed first shards have limited content diversity, SD14 is absent, and ImageNet-pretrained encoders may already have seen real source images.

Model selection: validation ROC-AUC only. Epoch selection: validation F1. Temperature minimizes Brier on calibration; decision threshold maximizes F1 on calibration. Test/OOD labels never fit weights, temperature or threshold. Test scores were inspected after each experiment, but candidate settings and selection rule stayed fixed. These test sets must not be reused for tuning.

## Actual test measurements

| Model | Accuracy / balanced accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| image-efficientnet-v1 | 0.677500 | 0.641434 | 0.805000 | 0.713969 | 0.774500 | 0.790840 | 0.194117 | 0.066399 |
| image-convnext-v1 | 0.630000 | 0.584416 | 0.900000 | 0.708661 | 0.776650 | 0.806095 | 0.204189 | 0.111090 |

## Seen generators versus held-out Midjourney

| Model | Seen test accuracy | Midjourney accuracy | Midjourney F1 | Midjourney ROC-AUC | OOD flag rate |
|---|---:|---:|---:|---:|---:|
| image-efficientnet-v1 | 0.677500 | 0.735000 | 0.770563 | 0.830100 | 0.070000 |
| image-convnext-v1 | 0.630000 | 0.660000 | 0.728000 | 0.789500 | 0.035000 |

OOD flag rate describes all 200 held-out-partition images (including real negatives); it is not generator-identification accuracy. Similar embedding distance does not prove an image is in-domain.

## Confusion matrices and calibration

- **image-efficientnet-v1:** test `[[TN, FP], [FN, TP]] = [[110, 90], [39, 161]]`; test false-positive rate 0.450000. Calibration Brier 0.189086 → 0.172621; calibration ECE 0.110381 → 0.088765.
- **image-convnext-v1:** test `[[TN, FP], [FN, TP]] = [[72, 128], [20, 180]]`; test false-positive rate 0.640000. Calibration Brier 0.175784 → 0.139251; calibration ECE 0.170870 → 0.059425.

Full-precision results, per-generator measurements, configs, split manifests, training history and ROC/PR/calibration/confusion plots are retained in `research/experiments/image-*/`. Per-generator subsets share the same 200 real negatives, so they have different class prevalence from the balanced aggregate.

## Installed artifact

- Selected: `convnext_tiny` by highest validation ROC-AUC.
- Version: `image-detector-v1-convnext_tiny`.
- Checkpoint: `models\image\project-trained-v1.pt`.
- SHA-256: `330358ba190af5037fe21ecf1b37e2bcdda9a233da8d61bead6f331c50780617`.
- Threshold: 0.30000000000000004; temperature: 0.28061551207734325.
- The previous external SigLIP files and registry are retained locally for rollback. They are not ensembled into these measurements.

## Real frontend upload verification

- **natural:** `images/validation-00868.jpeg`, ground-truth label 0, report `bab49bdb-38ba-4562-8d26-170fe9fb50bc`; actual AI probability 0.24068519, heuristic confidence 0.25000000, verdict `inconclusive`. Browser verified evidence, model tab, graph linkage and exported JSON. Risk estimate: `None`.
- **synthetic:** `images/validation-00985.png`, ground-truth label 1, report `598afc18-9010-4055-a578-e50f6ee57118`; actual AI probability 0.91431689, heuristic confidence 0.68663395, verdict `likely_ai_generated`. Browser verified evidence, model tab, graph linkage and exported JSON. Risk estimate: `None`.

Examples are the first real and synthetic entries in the frozen test manifest, selected without viewing predictions. Their correctness is not an acceptance test: integration tests require genuine inference and faithful presentation. Dark desktop and 390px mobile screenshots are in `docs/screenshots/trained-image-*.png`.

## Limits and display policy

This model has substantial classification errors. High general-purpose accuracy is **not established**. Documents, composites, screenshots and newer generators are outside this small evaluation. The app abstains when heuristic uncertainty is at least 0.65, embeddings exceed the validation 99th-percentile distance, transformations are unstable, or provenance conflicts. Confidence is a heuristic based on score ambiguity and sensitivity, not the probability that the answer is correct. Calibration is specific to this research subset.

Inference preserves the original calibrated probability and additionally checks a horizontal flip and JPEG quality 85. A 25-point spread or a class change across the calibrated cutoff raises uncertainty; these transformations are not independent model votes. No heatmap or pixel defect is fabricated. Missing provenance stays neutral. AI origin alone never increases security risk. Missing OCR/ClamAV or other detectors remain visible as incomplete coverage.

Image training, registry integration and uploaded-image inference are implemented and verified. Broader accuracy, audio/video task checkpoints, trained multimodal fusion and full-platform research acceptance remain incomplete.

Reproduction commands: [ML pipeline](ML_PIPELINE.md).

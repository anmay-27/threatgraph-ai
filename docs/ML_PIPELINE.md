# Reproducible model pipelines

Run commands from the repository root with Python 3.12/3.13. Install `backend/requirements.txt`, then `ml/requirements.txt`. Set `PYTHONPATH=backend:.` on Linux/macOS, or `$env:PYTHONPATH='backend;.'` in PowerShell. Fix dependency versions using the recorded environment snapshot when reproducing local measurements.

## URL classifier

```sh
python -m ml.url_detector.train --data-dir datasets/prepared/urls.csv --output-dir models/url --max-rows 30000 --seed 42
python -m ml.url_detector.infer --checkpoint models/url/best.joblib --url https://example.com/
python -m ml.url_detector.evaluate --checkpoint models/url/best.joblib --data-dir datasets/prepared/external.csv --output-dir research/results/url-external
```

The included run uses 17 lexical features, a reproducibly shuffled 30,000-row subset, domain-grouped 60/20/20 splits (counts vary with group size), three candidates, training-only three-fold grouped sigmoid calibration, and five validation thresholds. Validation F1 then PR-AUC select the final model. Only that model receives a final test evaluation. The historical test must not become a tuning set; use a genuinely external feed for further assessment.

Artifacts: best.joblib, registry.json, metrics.json, training_history.csv, config.json, split_manifest.json, and ROC/PR/calibration/confusion plots. `best.joblib` contains the preprocessing/calibration pipeline. No fake fallback model is shipped. Tree models are CPU-trained; neural CLI flags are accepted but unused by tabular estimators.

## Image / audio / video

```sh
python -m ml.image_detector.train --data-dir datasets/prepared/image --output-dir models/image --epochs 15 --batch-size 16 --lr 0.0001 --seed 42 --held-out-generator generator-held-out
python -m ml.audio_detector.train --data-dir datasets/prepared/audio --output-dir models/audio --epochs 15 --batch-size 16 --lr 0.0001 --seed 42
python -m ml.video_detector.train --data-dir datasets/prepared/video --output-dir models/video --epochs 15 --batch-size 16 --lr 0.0001 --seed 42
python -m ml.image_detector.infer --checkpoint models/image/best.pt --input sample.jpg
python -m ml.audio_detector.infer --checkpoint models/audio/best.pt --input sample.wav
python -m ml.video_detector.infer --checkpoint models/video/best.pt --input sample.mp4
python -m ml.image_detector.evaluate --checkpoint models/image/best.pt --data-dir datasets/prepared/image --split ood --output-dir research/results/image-ood
```

Image/video use pretrained ResNet18 or `--architecture efficientnet_b0`, a replaced binary head, balanced sampling, JPEG recompression/crop/blur/color augmentation, AdamW, cosine learning rate scheduling and early stopping. Pretrained torchvision weights require the first approved download. Audio uses mono 16 kHz log-Mel tensors and a CNN, with noise, down/up-sampling and quantization augmentation. It is not a pretrained speech encoder.

Training supports `--epochs --batch-size --lr --device --seed --data-dir --output-dir`. CUDA is selected when available; otherwise CPU. CUDA uses automatic mixed precision. Save best and last checkpoints, metrics, CSV history, split/config snapshots and plots. The last checkpoint is for inspection, not a full optimizer-resume snapshot.

Current image experiments fit temperature and decision threshold on a dedicated calibration partition. The `torch_media` adapter also uses diagonal normalized embedding distance with training statistics and a validation cutoff; this is not a validated unknown-generator detector. The `community_forensics` adapter loads official frozen ViT weights strictly, using the author's 440-pixel resize and 384-pixel center crop, and reports OOD as not estimated. Both retain original-image scores and flag flip/JPEG sensitivity. Abstention uses heuristic policy thresholds, not empirically validated selective-risk bounds.

Legacy video training metrics are **frame-level** on prepared face crops. The separately installed experimental VideoMAE adapter evaluates 16 whole frames together with a facial-domain gate; see [video screening](VIDEO_SCREENING.md). No independent video accuracy benchmark, robust multi-face tracking or lip synchronization evaluation has been completed.

## Learned fusion

```sh
python -m ml.fusion_model.train --data-dir datasets/prepared/investigations.jsonl --output-dir models/fusion --seed 42
python research/experiments/compare_fusion.py --data datasets/prepared/investigations.jsonl --output-dir research/results/fusion
```

Each JSONL case needs `label`, `group`, `evidence` (standard evidence objects), and `detector_predictions: "out_of_fold_or_external"`. Labels must come from independent ground truth, not the same heuristics being evaluated. Groups contain related campaigns/identities. Use out-of-fold base detector outputs or external models to prevent stacking leakage. Missing modalities use explicit masks; their numeric placeholder is 0.5, never zero-risk. The API loads a valid installed fusion registry automatically. Without one it explicitly reports an uncalibrated conservative rule baseline.

## Project-trained image experiment (October 2026)

The public acquisition and CPU experiments preserve the existing image API and registry. Run from the repository root after installing `ml/requirements.txt`:

```powershell
$env:TORCH_HOME = "$PWD/storage/torch"
$env:MPLCONFIGDIR = "$PWD/storage/matplotlib"
python datasets/scripts/download_genimage_subset.py
python datasets/scripts/prepare_genimage_subset.py
python -m ml.image_detector.train --data-dir datasets/prepared/tiny-genimage-v1 --output-dir research/experiments/image-efficientnet-v1 --architecture efficientnet_b0 --epochs 4 --batch-size 16 --lr 0.001 --patience 2 --threads 4 --freeze-backbone --held-out-generator Midjourney
python -m ml.image_detector.train --data-dir datasets/prepared/tiny-genimage-v1 --output-dir research/experiments/image-convnext-v1 --architecture convnext_tiny --epochs 4 --batch-size 16 --lr 0.001 --patience 2 --threads 4 --freeze-backbone --held-out-generator Midjourney
python scripts/install_trained_image.py research/experiments/image-efficientnet-v1 research/experiments/image-convnext-v1
```

Preparation and completed experiments are immutable: use a new versioned directory for new research. Downloads resume interrupted shards and verify pinned LFS SHA-256. Labels are 0=real, 1=AI-generated. Preparation retains source filenames and applies global exact/pixel/perceptual duplicate checks before balanced, seeded partitioning. Train/validation/calibration are derived only from source train; test and Midjourney OOD only from source validation. See `research/results/image_dataset_preparation.json` for counts, provenance and limitations. First-shard sampling has content bias; it is not the full GenImage benchmark.

Both experiments train binary heads on frozen ImageNet encoders, with JPEG/blur/crop/flip/color augmentation. Best epoch uses validation F1; temperature and threshold use a separate calibration partition. Candidate selection uses validation ROC-AUC only. OOD statistics use training embeddings and a validation distance cutoff. The raw calibrated original-image probability is preserved at inference; flip/recompression checks may raise uncertainty but never rewrite the score.

Results and limitations: [actual image experiment](IMAGE_TRAINING_RESULTS.md). The small CPU study does not establish high real-world accuracy. Training code can unfreeze final feature blocks with `--trainable-blocks`, but that was not done in these two reported experiments. New tuning requires fresh evaluation data.

After starting the API and built frontend, run `npx playwright test e2e/trained-image.spec.ts` from `frontend/`. It uploads fixed natural/synthetic test examples, verifies the report/model/graph/export, checks dark/mobile presentation and records actual scores. `python scripts/summarize_image_training.py` builds the report from measured experiment and browser artifacts. Do not mark upload verification complete without those artifacts.

## Official pretrained image candidate (v3)

This experiment freezes official Community Forensics weights and trains only a local scalar calibration. This project did not train the underlying vision model. Follow the [fixed protocol](IMAGE_V3_PROTOCOL.md); v1/v2 manifests and the unchanged v2 baseline checkpoint must already exist.

```powershell
python -m pip install -r ml/requirements.txt
python scripts/download_community_model.py
python datasets/scripts/download_genimage_subset.py --output-dir datasets/raw/tiny-genimage-v3 --train-shards 5 8 10 --validation-shards 3
python datasets/scripts/prepare_genimage_subset.py --raw-dir datasets/raw/tiny-genimage-v3 --output-dir datasets/prepared/tiny-genimage-v3 --train-per-class 200 --eval-per-class 200 --test-per-class 300 --exclude-manifest datasets/prepared/tiny-genimage-v1/manifest.csv datasets/prepared/tiny-genimage-v2/manifest.csv
$env:MPLCONFIGDIR = "$PWD/storage/matplotlib"
python -m scripts.evaluate_community_candidate
python scripts/install_image_v3.py
```

The installer preserves the current registry if the fixed comparison gate fails. Evaluation refuses to overwrite completed metrics. New tuning needs new held-out data. Safetensors, a pinned timm architecture and local preprocessing are used; downloaded repository Python is not executed.

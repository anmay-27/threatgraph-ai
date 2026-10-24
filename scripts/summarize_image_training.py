"""Publish measured artifacts as a readable local research report."""
import importlib.metadata
import json
import platform
from pathlib import Path


def main():
    comparison = json.loads(Path('research/results/image_training_comparison.json').read_text())
    registry = json.loads(Path('models/image/registry.json').read_text())
    lines = ['# Project-trained image detector: measured results', '',
             'This is a bounded CPU transfer-learning experiment, not a claim of production accuracy. Both candidates use frozen ImageNet encoders and trained binary heads. No Swin experiment was run because CUDA is unavailable.', '',
             '## Dataset and protocol', '',
             '[Tiny-GenImage](https://huggingface.co/datasets/TheKernel01/Tiny-GenImage), pinned revision `89c4fe9efd0ebc7ce5c7641ef57d578ccd639c69`. Two SHA-256-verified shards. Original benchmark: [GenImage](https://github.com/GenImage-Dataset/GenImage). Mirror declares CC-BY-NC-SA-4.0; underlying image rights remain with owners.', '',
             'Balanced partitions: train 800, model-selection validation 200, calibration 200, test 400, unseen-generator test 200 (100 Midjourney + 100 separate real images). Seed 42. Midjourney is excluded from fitting, model selection and calibration. Test/OOD use only the source validation partition. Global filename, decoded-pixel hash and pHash checks found no duplicates. Source prompt/scene family identifiers are unavailable, so semantic leakage cannot be ruled out. Fixed first shards have limited content diversity, SD14 is absent, and ImageNet-pretrained encoders may already have seen real source images.', '',
             'Model selection: validation ROC-AUC only. Epoch selection: validation F1. Temperature minimizes Brier on calibration; decision threshold maximizes F1 on calibration. Test/OOD labels never fit weights, temperature or threshold. Test scores were inspected after each experiment, but candidate settings and selection rule stayed fixed. These test sets must not be reused for tuning.', '',
             '## Actual test measurements', '',
             '| Model | Accuracy / balanced accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier | ECE |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name, result in comparison['experiments'].items():
        m = result['test']
        lines.append(f"| {Path(name).name} | {m['accuracy']:.6f} | {m['precision']:.6f} | {m['recall']:.6f} | {m['f1']:.6f} | {m['roc_auc']:.6f} | {m['pr_auc']:.6f} | {m['brier']:.6f} | {m['ece']:.6f} |")
    lines += ['', '## Seen generators versus held-out Midjourney', '', '| Model | Seen test accuracy | Midjourney accuracy | Midjourney F1 | Midjourney ROC-AUC | OOD flag rate |', '|---|---:|---:|---:|---:|---:|']
    for name, result in comparison['experiments'].items():
        m = result['held_out_generator']
        lines.append(f"| {Path(name).name} | {result['test']['accuracy']:.6f} | {m['accuracy']:.6f} | {m['f1']:.6f} | {m['roc_auc']:.6f} | {result['ood_flag_rate']:.6f} |")
    lines += ['', 'OOD flag rate describes all 200 held-out-partition images (including real negatives); it is not generator-identification accuracy. Similar embedding distance does not prove an image is in-domain.', '', '## Confusion matrices and calibration', '']
    for name, result in comparison['experiments'].items():
        lines += [f"- **{Path(name).name}:** test `[[TN, FP], [FN, TP]] = {result['test']['confusion_matrix']}`; test false-positive rate {result['test']['false_positive_rate']:.6f}. Calibration Brier {result['calibration_before']['brier']:.6f} → {result['calibration']['brier']:.6f}; calibration ECE {result['calibration_before']['ece']:.6f} → {result['calibration']['ece']:.6f}."]
    lines += ['', 'Full-precision results, per-generator measurements, configs, split manifests, training history and ROC/PR/calibration/confusion plots are retained in `research/experiments/image-*/`. Per-generator subsets share the same 200 real negatives, so they have different class prevalence from the balanced aggregate.', '', '## Installed artifact', '',
              f"- Selected: `{registry['architecture']}` by highest validation ROC-AUC.", f"- Version: `{registry['version']}`.", f"- Checkpoint: `{comparison['checkpoint']}`.", f"- SHA-256: `{comparison['sha256']}`.", f"- Threshold: {registry['threshold']}; temperature: {registry['temperature']}.",
              '- The previous external SigLIP files and registry are retained locally for rollback. They are not ensembled into these measurements.', '', '## Real frontend upload verification', '']
    for name in ['natural', 'synthetic']:
        path = Path(f'research/results/image-upload-{name}.json')
        result = json.loads(path.read_text())
        model = result['model']
        lines += [f"- **{name}:** `{result['sample']}`, ground-truth label {result['ground_truth']}, report `{result['report_id']}`; actual AI probability {model['score']:.8f}, heuristic confidence {model['confidence']:.8f}, verdict `{model['metadata']['verdict']}`. Browser verified evidence, model tab, graph linkage and exported JSON. Risk estimate: `{result['risk_score']}`."]
    lines += ['', 'Examples are the first real and synthetic entries in the frozen test manifest, selected without viewing predictions. Their correctness is not an acceptance test: integration tests require genuine inference and faithful presentation. Dark desktop and 390px mobile screenshots are in `docs/screenshots/trained-image-*.png`.', '',
              '## Limits and display policy', '',
              'This model has substantial classification errors. High general-purpose accuracy is **not established**. Documents, composites, screenshots and newer generators are outside this small evaluation. The app abstains when heuristic uncertainty is at least 0.65, embeddings exceed the validation 99th-percentile distance, transformations are unstable, or provenance conflicts. Confidence is a heuristic based on score ambiguity and sensitivity, not the probability that the answer is correct. Calibration is specific to this research subset.', '',
              'Inference preserves the original calibrated probability and additionally checks a horizontal flip and JPEG quality 85. A 25-point spread or a class change across the calibrated cutoff raises uncertainty; these transformations are not independent model votes. No heatmap or pixel defect is fabricated. Missing provenance stays neutral. AI origin alone never increases security risk. Missing OCR/ClamAV or other detectors remain visible as incomplete coverage.', '',
              'Image training, registry integration and uploaded-image inference are implemented and verified. Broader accuracy, audio/video task checkpoints, trained multimodal fusion and full-platform research acceptance remain incomplete.', '', 'Reproduction commands: [ML pipeline](ML_PIPELINE.md).']
    Path('docs/IMAGE_TRAINING_RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    versions = {package: importlib.metadata.version(package) for package in ['torch', 'torchvision', 'numpy', 'scikit-learn', 'Pillow', 'pyarrow', 'scipy']}
    Path('research/results/image_training_environment.json').write_text(json.dumps(dict(python=platform.python_version(), platform=platform.platform(), packages=versions), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()


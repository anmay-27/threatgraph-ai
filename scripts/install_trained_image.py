"""Select by validation ROC-AUC only; preserve the previously installed registry."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('experiments', nargs='+', type=Path)
    args = parser.parse_args()
    records = [(path, json.loads((path / 'metrics.json').read_text())) for path in args.experiments]
    selected, metrics = max(records, key=lambda item: item[1]['validation']['roc_auc'])
    registry = json.loads((selected / 'registry.json').read_text())
    destination = Path('models/image')
    destination.mkdir(exist_ok=True, parents=True)
    previous = destination / 'registry.json'
    archive = destination / 'registry-before-project-training.json'
    if previous.exists() and not archive.exists():
        shutil.copy2(previous, archive)
    artifact = destination / 'project-trained-v1.pt'
    shutil.copy2(selected / 'best.pt', artifact)
    with artifact.open('rb') as file:
        checksum = hashlib.file_digest(file, 'sha256').hexdigest()
    registry.update(file_path=artifact.name, version='image-detector-v1-' + registry['architecture'], sha256=checksum,
                    selection_criterion='Highest validation ROC-AUC, no test/OOD score used for selection', experiment=str(selected),
                    training_dataset='Tiny-GenImage fixed-shard subset (1,800 images, 800 training)',
                    dataset_revision='89c4fe9efd0ebc7ce5c7641ef57d578ccd639c69', license='Research data: CC-BY-NC-SA-4.0 mirror declaration; underlying image rights remain',
                    limitation='Small fixed-shard research subset, limited source diversity, SD14 absent. ImageNet pretraining overlaps source collection. Unseen generators, documents and screenshots may fail. Calibration is dataset-specific; synthetic origin does not establish malicious intent.')
    temporary = destination / 'registry.pending.json'
    temporary.write_text(json.dumps(registry, indent=2), encoding='utf-8')
    temporary.replace(previous)
    summary = dict(selection_criterion=registry['selection_criterion'], selected=str(selected), checkpoint=str(artifact), sha256=checksum,
                   experiments={str(path): result for path, result in records})
    Path('research/results/image_training_comparison.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'experiments'}, indent=2))


if __name__ == '__main__':
    main()

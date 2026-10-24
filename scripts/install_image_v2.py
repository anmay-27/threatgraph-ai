"""Apply the documented, fixed deployment gate without tuning on test labels."""
import hashlib
import json
import shutil
from pathlib import Path

def main():
    experiment = Path('research/experiments/image-efficientnet-v2')
    results = json.loads((experiment / 'metrics.json').read_text())
    baseline = json.loads(Path('research/experiments/image-v1-on-v2/metrics.json').read_text())
    passed = results['test']['balanced_accuracy'] > baseline['test']['balanced_accuracy'] and results['test']['false_positive_rate'] < .25
    audit = {'gate': 'v2 balanced accuracy > v1 on identical fresh test AND v2 FPR <25%', 'passed': passed, 'baseline': baseline, 'candidate': results}
    Path('research/results/image-v2-deployment-gate.json').write_text(json.dumps(audit, indent=2))
    if not passed:
        print('Gate failed; preserving installed model.', flush=True)
        return
    directory = Path('models/image')
    prior = directory / 'registry.json'
    archive = directory / 'registry-before-v2.json'
    if not archive.exists():
        shutil.copyfile(prior, archive)
    target = directory / 'project-trained-v2.pt'
    shutil.copyfile(experiment / 'best.pt', target)
    record = json.loads((experiment / 'registry.json').read_text())
    record.update(version='image-detector-v2-efficientnet_b0', file_path=target.name, sha256=hashlib.sha256(target.read_bytes()).hexdigest(), experiment=str(experiment), deployment_gate=str(Path('research/results/image-v2-deployment-gate.json')), limitation='Small pinned GenImage derivative; not representative of current generators, screenshots, documents or all photographs. Held-out test is 600 images; separate Midjourney evaluation is 200 images. Temperature calibration and cutoff are dataset-specific. Synthetic origin does not establish malicious intent.')
    prior.write_text(json.dumps(record, indent=2))
    print(json.dumps({'installed': record['version'], 'threshold': record['threshold'], 'test': results['test'], 'ood': results.get('held_out_generator')}, indent=2), flush=True)

if __name__ == '__main__':
    main()

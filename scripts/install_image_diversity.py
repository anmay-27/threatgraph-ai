"""Explicit local experimental installation; preserve baseline and release status."""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import load_file, save_file

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.common import community_image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--activate-experimental', action='store_true')
    args = parser.parse_args()
    experiment = ROOT / 'research/experiments/image-diversity-v1'
    destination = ROOT / 'models/image/community-diversity-v1'
    baseline = ROOT / 'models/image/community-forensics-384/model.safetensors'
    adapter = json.loads((experiment / 'adapter.json').read_text())
    metrics = json.loads((experiment / 'metrics.json').read_text())
    digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
    if digest != adapter['base_sha256']:
        raise ValueError('Base checkpoint does not match trained adapter')
    state = load_file(str(baseline))
    mean, scale, weight = (torch.tensor(adapter[k], dtype=torch.float64) for k in ('mean', 'scale', 'weights'))
    if not all(torch.isfinite(t).all() for t in (mean, scale, weight)) or not (scale > 0).all():
        raise ValueError('Invalid adapter')
    original_weight = state['vit.head.weight'].double()
    original_bias = state['vit.head.bias'].double()
    state['vit.head.weight'] = (original_weight + (weight / scale).unsqueeze(0)).float()
    state['vit.head.bias'] = (original_bias + adapter['bias'] - (mean * weight / scale).sum()).float()
    # Verify exported float32 head against saved residual predictions on every cache.
    maximum_error = 0.
    for cache in experiment.glob('features-*.npz'):
        with np.load(cache) as data:
            features = torch.tensor(data['x'], dtype=torch.float64)
            expected = torch.tensor(data['z'], dtype=torch.float64) + ((features - mean) / scale) @ weight + adapter['bias']
            actual = features @ state['vit.head.weight'].double().T + state['vit.head.bias'].double()
            maximum_error = max(maximum_error, float((actual.reshape(-1) - expected).abs().max()))
    if maximum_error > .001:
        raise ValueError(f'Export mismatch: {maximum_error}')
    destination.mkdir(parents=True, exist_ok=True)
    checkpoint = destination / 'model.safetensors'
    save_file(state, str(checkpoint))
    shutil.copy2(baseline.with_name('config.json'), destination / 'config.json')
    checksum = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    calibration = dict(temperature=adapter['temperature'], threshold=adapter['threshold'], partition='image-diversity-v1: calibration only (legacy, modern, diverse)', method='temperature_scaling', checkpoint_sha256=checksum, threshold_rule='Maximize worst-source balanced accuracy subject to per-source calibration FPR <=2.5%')
    (destination / 'calibration.json').write_text(json.dumps(calibration, indent=2))
    rows = json.loads((experiment / 'features.json').read_text())['rows']
    selected = []
    for source in ('legacy', 'modern', 'diverse'):
        for label in (0, 1):
            selected.extend(sorted((r for r in rows if r['source'] == source and r['split'] == 'validation' and r['label'] == label), key=lambda r: r['path'])[:2])
    audit = []
    for row in selected:
        result = community_image.infer(ROOT / row['path'], checkpoint)
        audit.append(dict(source=row['source'], label=row['label'], **result))
        print(f"Stability smoke {len(audit)}/{len(selected)}: {result['verdict']}", flush=True)
    summary = dict(count=len(audit), maximum_export_logit_error=maximum_error, unstable_count=sum(r['unstable'] for r in audit), inconclusive_count=sum(r['verdict'] == 'inconclusive' for r in audit), scope='12 fixed validation examples, original/mirror/JPEG85; integration smoke only, not a population stability guarantee', samples=audit)
    (experiment / 'installation-smoke.json').write_text(json.dumps(summary, indent=2))
    if not args.activate_experimental:
        print('Export and smoke completed; registry unchanged.')
        return
    registry_path = ROOT / 'models/image/registry.json'
    archive = ROOT / 'models/image/registry-before-diversity-v1.json'
    if not archive.exists():
        shutil.copy2(registry_path, archive)
    previous = json.loads(archive.read_text())
    record = {k: previous[k] for k in ('name', 'architecture', 'runtime', 'classes')}
    record.update(version='image-detector-v4-diversity-experimental', file_path='community-diversity-v1/model.safetensors', sha256=checksum, threshold=adapter['threshold'], temperature=adapter['temperature'], calibration='temperature_scaling', calibration_date=datetime.now(timezone.utc).isoformat(), deployment_status='experimental_local', training_dataset='Frozen Community Forensics encoder; residual head fitted on 12,568 local GenImage/TextRich images', test_metrics=metrics['fresh_holdout'], regression_metrics=metrics['candidate'], experiment=str(experiment.relative_to(ROOT)), deployment_gate_passed=False, activation_reason='User-requested local experimental replacement; not a release-gate pass', limitation='Experimental locally trained head. Fresh 500-image same-source test: 97.6% accuracy; not guaranteed field accuracy. Some previous tests regressed. Upstream pretraining overlap is unknown. Only a 12-image transformation smoke check; uncertainty safeguards remain active. Research data restrictions apply.')
    temporary = registry_path.with_suffix('.pending.json')
    temporary.write_text(json.dumps(record, indent=2))
    temporary.replace(registry_path)
    (experiment / 'activation.json').write_text(json.dumps(dict(version=record['version'], backup=str(archive), sha256=checksum, experimental=True), indent=2))
    print('Activated ' + record['version'], flush=True)


if __name__ == '__main__':
    import os
    os.chdir(ROOT)
    main()

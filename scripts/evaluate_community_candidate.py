"""Fixed v3 calibration and paired evaluation; never optimize using test labels."""
import gc
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from ml.common import community_image
from ml.common.data import read_manifest, MediaDataset
from ml.common.inference import load as load_baseline
from ml.common.train import predict
from ml.common.metrics import metrics, save_json, plots

ROOT = Path('datasets/prepared/tiny-genimage-v3')
OUTPUT = Path('research/experiments/image-community-v3')
CHECKPOINT = Path('models/image/community-forensics-384/model.safetensors')


class Images(Dataset):
    def __init__(self, rows):
        self.rows = rows
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, i):
        with Image.open(ROOT / self.rows[i]['path']) as image:
            return community_image.image_tensor(image)


def logits(model, rows, split):
    values = []
    with torch.inference_mode():
        for batch in DataLoader(Images(rows), batch_size=4, num_workers=0):
            values.extend(model(batch).reshape(-1).tolist())
            if len(values) % 100 == 0:
                print(f'{split}: {len(values)}/{len(rows)}', flush=True)
    if not np.isfinite(values).all():
        raise ValueError('Non-finite model output')
    return np.asarray(values)


def sigmoid(logits, temperature=1):
    return 1 / (1 + np.exp(-np.clip(logits/temperature, -50, 50)))


def calibrate(y, z):
    temperature = float(min(np.geomspace(.25,4,25), key=lambda t: metrics(y,sigmoid(z,t))['brier']))
    p = sigmoid(z,temperature)
    candidates = [(float(t),metrics(y,p,t)) for t in np.linspace(.01,1,100)]
    eligible = [(t,m) for t,m in candidates if m['false_positive_rate'] <= .2]
    if not eligible:
        raise ValueError('No calibration threshold meets the fixed FPR constraint')
    threshold = max(eligible,key=lambda x:(x[1]['balanced_accuracy'],x[1]['recall'],x[0]))[0]
    return dict(temperature=temperature,threshold=threshold,partition=str(ROOT / 'manifest.csv') + ':calibration', method='temperature_scaling', threshold_rule='maximum calibration balanced accuracy subject to FPR <=20%')


def main():
    if (OUTPUT / 'metrics.json').exists():
        raise ValueError('Candidate already evaluated; do not tune against this test set')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    rows = read_manifest(ROOT)
    splits = {s:[r for r in rows if r['split']==s] for s in ['calibration','validation','test','ood']}
    for split, items in splits.items():
        if not items or {int(r['label']) for r in items} != {0,1}:
            raise ValueError('Missing or invalid split: '+split)
    model = community_image.load(str(CHECKPOINT), CHECKPOINT.stat().st_mtime_ns)
    cz = logits(model,splits['calibration'],'calibration')
    cy = np.array([int(r['label']) for r in splits['calibration']])
    calibration = calibrate(cy,cz)
    save_json(OUTPUT / 'calibration.json',calibration)
    # Parameters locked and written before final test predictions are produced.
    candidate, predictions = {}, {}
    candidate['calibration'] = metrics(cy,sigmoid(cz,calibration['temperature']),calibration['threshold'])
    for split in ['validation','test','ood']:
        z = logits(model,splits[split],split)
        y = np.array([int(r['label']) for r in splits[split]])
        p = sigmoid(z,calibration['temperature'])
        candidate[split] = metrics(y,p,calibration['threshold'])
        predictions[split] = [dict(path=r['path'],label=int(r['label']),generator=r['generator'],logit=float(v),probability=float(q)) for r,v,q in zip(splits[split],z,p)]
    del model
    community_image.load.cache_clear()
    gc.collect()
    path = Path('models/image/project-trained-v2.pt')
    model, checkpoint = load_baseline(str(path),path.stat().st_mtime_ns)
    baseline = {}
    for split in ['test','ood']:
        y,z,_ = predict(model,DataLoader(MediaDataset(ROOT,splits[split],'image',False),batch_size=8),'cpu')
        p = sigmoid(z,checkpoint['temperature'])
        baseline[split] = metrics(y,p,checkpoint['threshold'])
        for item, q in zip(predictions[split],p):
            item['baseline_probability'] = float(q)
        print('Baseline completed',split,flush=True)
    candidate['per_generator'] = {}
    test = predictions['test']
    for generator in sorted({r['generator'] for r in test if r['label']==1}):
        subset = [r for r in test if r['label']==0 or r['generator']==generator]
        candidate['per_generator'][generator] = metrics([r['label'] for r in subset],[r['probability'] for r in subset],calibration['threshold'])
    new, old = candidate['test'], baseline['test']
    passed = (new['balanced_accuracy'] >= old['balanced_accuracy']+.02 and new['recall'] >= old['recall'] and new['false_positive_rate'] <= old['false_positive_rate'] and candidate['ood']['balanced_accuracy'] >= baseline['ood']['balanced_accuracy'])
    y = np.asarray([r['label'] for r in test])
    delta = ((np.asarray([r['probability'] for r in test]) >= calibration['threshold']) == y).astype(float) - ((np.asarray([r['baseline_probability'] for r in test]) >= checkpoint['threshold']) == y).astype(float)
    rng = np.random.default_rng(42)
    groups = [np.where(y==label)[0] for label in (0,1)]
    bootstrap = [float(delta[np.concatenate([rng.choice(g,len(g),replace=True) for g in groups])].mean()) for _ in range(2000)]
    audit = dict(candidate=candidate,baseline=baseline,calibration=calibration,passed_deployment_gate=passed,paired_accuracy_difference=float(delta.mean()),paired_bootstrap_95_interval=np.quantile(bootstrap,[.025,.975]).tolist(),bootstrap_repetitions=2000,model_sha256=hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),manifest_sha256=hashlib.sha256((ROOT/'manifest.csv').read_bytes()).hexdigest(),limitations='Local comparison only. Third-party pretraining/training overlap with benchmark images cannot be excluded. No validated OOD gate or field-accuracy claim.')
    save_json(OUTPUT / 'predictions.json',predictions)
    save_json(OUTPUT / 'metrics.json',audit)
    plots(y,[r['probability'] for r in test],OUTPUT/'plots',calibration['threshold'])
    print(json.dumps({k:v for k,v in audit.items() if k not in {'candidate','baseline'}}),flush=True)
    print('Candidate test',new,'Baseline test',old,flush=True)

if __name__ == '__main__':
    main()

"""Add unused, deduplicated local samples, cache embeddings, fit balanced head."""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
import train_image_mvp as base
import train_image_balanced as balanced

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/experiments/image-diversity-v1'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'metrics.json').exists():
        print('Experiment already finalized; results preserved.')
        return
    prepared = ROOT / 'datasets/prepared/image-diversity'
    if not (prepared / 'manifest.csv').exists():
        subprocess.run([sys.executable, '-u', 'datasets/scripts/prepare_image_10k.py', '--diversity-round'], cwd=ROOT, check=True)
    original = ROOT / 'research/experiments/image-10k'
    metadata = json.loads((original / 'features.json').read_text())
    rows = metadata['rows']
    checkpoint = base.CHECKPOINT.read_bytes()
    if hashlib.sha256(json.dumps(rows, sort_keys=True).encode() + checkpoint).hexdigest() != metadata['fingerprint']:
        raise ValueError('Original feature fingerprint mismatch')
    for row in csv.DictReader((prepared / 'manifest.csv').open()):
        rows.append(dict(path=str(prepared / row['path']), label=int(row['label']), split=row['split'], source='diverse', category=row['generator']))
    fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode() + checkpoint).hexdigest()
    (OUT / 'features.json').write_text(json.dumps(dict(fingerprint=fingerprint, rows=rows)))
    model = None
    for start in range(0, len(rows), 100):
        subset = rows[start:start+100]
        key = hashlib.sha256(json.dumps(subset, sort_keys=True).encode() + str(base.CHECKPOINT.stat().st_mtime_ns).encode()).hexdigest()[:20]
        cache = OUT / f'features-{key}.npz'
        if cache.exists():
            continue
        previous = original / cache.name
        if previous.exists():
            shutil.copyfile(previous, cache)
            continue
        if model is None:
            model = base.community_image.load(str(base.CHECKPOINT), base.CHECKPOINT.stat().st_mtime_ns)
        x, z = [], []
        with torch.inference_mode():
            for batch in DataLoader(base.Images(subset), batch_size=4, num_workers=0):
                embedding = model.forward_head(model.forward_features(batch), pre_logits=True)
                x.extend(embedding.numpy())
                z.extend(model.head(embedding).reshape(-1).numpy())
        np.savez_compressed(cache, x=np.asarray(x), z=np.asarray(z))
        print(f'Encoder features: {min(start+100,len(rows))}/{len(rows)}', flush=True)
    balanced.CACHE = OUT
    balanced.OUT = OUT
    balanced.main()


if __name__ == '__main__':
    import os
    os.chdir(ROOT)
    main()

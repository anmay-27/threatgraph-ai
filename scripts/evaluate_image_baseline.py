"""Evaluate the unchanged installed image baseline on the fresh v2 partition."""
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
from ml.common.data import read_manifest, MediaDataset
from ml.common.inference import load
from ml.common.train import predict
from ml.common.metrics import metrics, save_json

def main():
    output = Path('research/experiments/image-v1-on-v2')
    if (output / 'metrics.json').exists():
        raise ValueError('Baseline already evaluated')
    root = Path('datasets/prepared/tiny-genimage-v2')
    path = Path('models/image/project-trained-v1.pt')
    model, checkpoint = load(str(path), path.stat().st_mtime_ns)
    torch.set_num_threads(2)
    results = {}
    for split in ['test', 'ood']:
        rows = [r for r in read_manifest(root) if r['split'] == split]
        y, logits, _ = predict(model, DataLoader(MediaDataset(root, rows, 'image', False), batch_size=16), 'cpu')
        probabilities = 1 / (1 + np.exp(-np.clip(logits / checkpoint['temperature'], -50, 50)))
        results[split] = metrics(y, probabilities, checkpoint['threshold'])
    save_json(output / 'metrics.json', results)
    print(results, flush=True)

if __name__ == '__main__':
    main()

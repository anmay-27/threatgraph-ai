"""Source-balanced follow-up; prior tests are regression checks, not fresh evidence."""
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
import train_image_mvp as base

OUT = Path('research/experiments/image-balanced-v1')
CACHE = Path('research/experiments/image-10k')


def main():
    torch.set_num_threads(4)
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'metrics.json').exists():
        raise RuntimeError('Finalized experiment; do not retune on regression results')
    metadata = json.loads((CACHE / 'features.json').read_text())
    rows = metadata['rows']
    fingerprint = hashlib.sha256(json.dumps(rows, sort_keys=True).encode() + base.CHECKPOINT.read_bytes()).hexdigest()
    if fingerprint != metadata['fingerprint']:
        raise ValueError('Encoder fingerprint mismatch')
    chunks = []
    for start in range(0, len(rows), 100):
        key = hashlib.sha256(json.dumps(rows[start:start+100], sort_keys=True).encode() + str(base.CHECKPOINT.stat().st_mtime_ns).encode()).hexdigest()[:20]
        with np.load(CACHE / f'features-{key}.npz') as chunk:
            chunks.append((chunk['x'].copy(), chunk['z'].copy()))
    x = np.concatenate([c[0] for c in chunks]).astype(np.float64)
    z = np.concatenate([c[1] for c in chunks]).astype(np.float64)
    y = np.array([r['label'] for r in rows])
    split = np.array([r['split'] for r in rows])
    source = np.array([r['source'] for r in rows])
    train, val, cal = (split == s for s in ('train', 'validation', 'calibration'))
    domains = sorted(set(source[train]))
    mean, scale = x[train].mean(0), np.maximum(x[train].std(0), .01)
    sx = (x - mean) / scale
    weights = np.zeros(len(rows))
    for domain in domains:
        for label in (0, 1):
            mask = train & (source == domain) & (y == label)
            if not mask.any():
                raise ValueError('Missing training stratum')
            weights[mask] = 1 / mask.sum()
    weights = weights[train] / weights[train].mean()
    tx, tz, ty, tw = map(torch.tensor, (sx[train], z[train], y[train].astype(float), weights))
    choices = []
    for penalty in (.1, 1., 10.):
        w = torch.zeros(x.shape[1], dtype=torch.float64, requires_grad=True)
        b = torch.zeros((), dtype=torch.float64, requires_grad=True)
        optimizer = torch.optim.LBFGS([w, b], max_iter=100, line_search_fn='strong_wolfe')

        def closure():
            optimizer.zero_grad()
            loss = (torch.nn.functional.binary_cross_entropy_with_logits(tz + tx @ w + b, ty, reduction='none') * tw).mean() + penalty * (w.square().sum() + b.square())
            loss.backward()
            return loss

        optimizer.step(closure)
        weight, bias = w.detach().numpy(), float(b.detach())
        logits = z + sx @ weight + bias
        score = max(base.nll(y[val & (source == d)], logits[val & (source == d)]) for d in domains)
        choices.append((score, penalty, weight, bias, logits))
        print(f'Fitted penalty={penalty}; worst-domain validation NLL={score:.5f}', flush=True)
    _, penalty, weight, bias, logits = min(choices, key=lambda c: c[0])
    temperature = float(min(np.geomspace(.25, 8, 40), key=lambda t: np.mean([base.nll(y[cal & (source == d)], logits[cal & (source == d)] / t) for d in domains])))
    p = base.sigmoid(logits / temperature)
    candidates = []
    for threshold in np.linspace(.01, .99, 99):
        groups = [base.metrics(y[cal & (source == d)], p[cal & (source == d)], threshold) for d in domains]
        if all(g['false_positive_rate'] <= .025 for g in groups):
            candidates.append((min(g['balanced_accuracy'] for g in groups), float(threshold)))
    threshold = max(candidates)[1] if candidates else 1.
    adapter = dict(schema=1, base_sha256=hashlib.sha256(base.CHECKPOINT.read_bytes()).hexdigest(), mean=mean.tolist(), scale=scale.tolist(), weights=weight.tolist(), bias=bias, temperature=temperature, threshold=threshold, penalty=penalty, fit_count=int(train.sum()), calibration_count=int(cal.sum()), feature_fingerprint=fingerprint)
    (OUT / 'adapter.json').write_text(json.dumps(adapter, indent=2))
    # Freeze parameters before opening regression labels for evaluation.
    result = dict(training_count=int(train.sum()), threshold=threshold, candidate={}, installed_model_changed=False, deployment_gate_passed=False, decision='Research candidate only: fresh holdout and transform-stability evaluation required', limits=['Reuses previously examined test sets for regression checks.', 'No new images added; encoder remains frozen.', 'Source balancing does not establish generalization to new generators.'])
    for name, mask in [('legacy_test', (source == 'legacy') & (split == 'test')), ('legacy_ood', (source == 'legacy') & (split == 'ood')), ('modern_test', (source == 'modern') & (split == 'test')), ('prior_posters', source == 'poster')]:
        result['candidate'][name] = base.metrics(y[mask], p[mask], threshold)
    fresh = (source == 'diverse') & (split == 'test')
    if fresh.any():
        result['fresh_holdout'] = base.metrics(y[fresh], p[fresh], threshold)
        result['limits'] = ['Prior test sets are regression checks.', 'Fresh holdout is from the same dataset mirror; upstream pretraining overlap is unknown.', 'Midjourney now enters training; old OOD scores no longer measure unseen-generator generalization.', 'No automatic installation; transformation stability remains untested.']
    (OUT / 'metrics.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()

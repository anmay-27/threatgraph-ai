"""Audit the frozen score-only abstention rule; never tune on test labels."""
import json
from pathlib import Path
import numpy as np


def main():
    root = Path('research/experiments/image-convnext-v1')
    rows = json.loads((root / 'test_predictions.json').read_text())
    threshold = json.loads((root / 'registry.json').read_text())['threshold']
    scores = np.array([r['probability'] for r in rows])
    labels = np.array([r['label'] for r in rows])
    accepted = 4 * scores * (1 - scores) < .65
    errors = (scores >= threshold) != labels
    result = dict(experiment=str(root), threshold=threshold, uncertainty_cutoff=.65,
                  scope='Original-image scores only. Excludes embedding OOD, transformation instability, provenance and document cautions. This is NOT full deployed-policy accuracy.',
                  test_count=len(rows), accepted_count=int(accepted.sum()), coverage=float(accepted.mean()),
                  accepted_errors=int(errors[accepted].sum()), accepted_error_rate=float(errors[accepted].mean()),
                  overall_errors=int(errors.sum()), policy_changed=False,
                  conclusion='Abstention reduces coverage but does not eliminate errors. Heuristic confidence must not be described as measured correctness probability.')
    Path('research/results/image_abstention_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

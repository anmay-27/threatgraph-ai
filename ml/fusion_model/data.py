import json
import numpy as np
from app.schemas.evidence import Evidence
from app.fusion.engine import conflicts
from app.fusion.features import vector


def load(path, use_conflicts=True, use_uncertainty=True):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    evidence = [[Evidence(**e) for e in row["evidence"]] for row in rows]
    x = np.array(
        [
            vector(items, conflicts(items), use_conflicts, use_uncertainty)
            for items in evidence
        ]
    )
    y = np.array([int(row["label"]) for row in rows])
    groups = np.array([row["group"] for row in rows])
    if any(
        row.get("detector_predictions") != "out_of_fold_or_external" for row in rows
    ):
        raise ValueError(
            "Fusion rows must attest out-of-fold or external base detector predictions"
        )
    return x, y, groups, evidence

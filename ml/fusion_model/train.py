"""Train a calibrated fusion model on independently labeled investigations."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.calibration import CalibratedClassifierCV
from ml.fusion_model.data import load
from ml.fusion_model.model import build
from ml.common.metrics import metrics, save_json, plots


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=0.001)
    p.add_argument("--device", default="cpu")
    a = p.parse_args()
    if (a.output_dir / "metrics.json").exists():
        raise ValueError("Use a new experiment output directory")
    a.output_dir.mkdir(parents=True, exist_ok=True)
    x, y, groups, _ = load(a.data_dir)
    tv, test = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=a.seed).split(
            x, y, groups
        )
    )
    tr, va = next(
        GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=a.seed + 1).split(
            x[tv], y[tv], groups[tv]
        )
    )
    train, val = tv[tr], tv[va]
    cv = list(
        StratifiedGroupKFold(3, shuffle=True, random_state=a.seed).split(
            x[train], y[train], groups[train]
        )
    )
    model = CalibratedClassifierCV(build(a.seed), method="sigmoid", cv=cv).fit(
        x[train], y[train]
    )
    vp = model.predict_proba(x[val])[:, 1]
    threshold = float(
        max(np.linspace(0.2, 0.8, 25), key=lambda t: metrics(y[val], vp, t)["f1"])
    )
    tp = model.predict_proba(x[test])[:, 1]
    results = {
        "validation": metrics(y[val], vp, threshold),
        "test": metrics(y[test], tp, threshold),
    }
    joblib.dump(model, a.output_dir / "best.joblib")
    save_json(a.output_dir / "metrics.json", results)
    save_json(a.output_dir / "config.json", {k: str(v) for k, v in vars(a).items()})
    save_json(
        a.output_dir / "registry.json",
        {
            "name": "fusion",
            "version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "architecture": "masked-logistic-sigmoid",
            "training_dataset": str(a.data_dir),
            "date_trained": datetime.now(timezone.utc).isoformat(),
            "validation_metrics": results["validation"],
            "test_metrics": results["test"],
            "threshold": threshold,
            "file_path": "best.joblib",
        },
    )
    plots(y[test], tp, a.output_dir / "plots")
    print(results)


if __name__ == "__main__":
    main()

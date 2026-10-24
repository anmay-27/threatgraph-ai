import argparse
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedGroupKFold
from ml.url_detector.data import load
from ml.url_detector.model import candidates
from ml.common.metrics import metrics, save_json, plots
from app.analyzers.url.features import FEATURE_NAMES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="CSV or directory containing urls.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("models/url"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument(
        "--epochs", type=int, default=20, help="Reserved for neural alternatives"
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    path = args.data_dir / "urls.csv" if args.data_dir.is_dir() else args.data_dir
    output = args.output_dir
    if (output / "metrics.json").exists():
        raise ValueError(
            "Use a new output directory; do not repeatedly tune against an evaluated test set"
        )
    output.mkdir(parents=True, exist_ok=True)
    x, y, groups, splits = load(path, args.seed, args.max_rows)
    train, val, test = (splits[k] for k in ("train", "validation", "test"))
    save_json(
        output / "config.json",
        {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
    )
    save_json(
        output / "split_manifest.json",
        {
            "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "counts": {k: len(v) for k, v in splits.items()},
            "groups": {k: sorted(set(groups[v])) for k, v in splits.items()},
        },
    )
    cv = list(
        StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=args.seed).split(
            x[train], y[train], groups[train]
        )
    )
    best = None
    history = []
    for name, estimator in candidates(args.seed).items():
        print("Training", name, flush=True)
        model = CalibratedClassifierCV(estimator, method="sigmoid", cv=cv, n_jobs=1)
        model.fit(x[train], y[train])
        p = model.predict_proba(x[val])[:, 1]
        # Threshold and candidate selection use validation only.
        choices = [
            (threshold, metrics(y[val], p, threshold))
            for threshold in (0.3, 0.4, 0.5, 0.6, 0.7)
        ]
        threshold, result = max(
            choices, key=lambda item: (item[1]["f1"], item[1]["pr_auc"])
        )
        history.append({"model": name, "threshold": threshold, **result})
        print(name, result, flush=True)
        if best is None or (result["f1"], result["pr_auc"]) > (
            best[3]["f1"],
            best[3]["pr_auc"],
        ):
            best = (name, model, threshold, result)
    name, model, threshold, validation = best
    # Exactly one final test evaluation, after all selection decisions.
    probabilities = model.predict_proba(x[test])[:, 1]
    evaluation = metrics(y[test], probabilities, threshold)
    joblib.dump(model, output / "best.joblib")
    save_json(
        output / "metrics.json",
        {"validation": validation, "test": evaluation, "candidates": history},
    )
    save_json(
        output / "registry.json",
        {
            "name": "url",
            "version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "architecture": name,
            "training_dataset": str(path),
            "date_trained": datetime.now(timezone.utc).isoformat(),
            "validation_metrics": validation,
            "test_metrics": evaluation,
            "threshold": threshold,
            "file_path": "best.joblib",
            "feature_names": FEATURE_NAMES,
            "calibration": "sigmoid; domain-disjoint 3-fold training CV",
            "deployment_status": "experimental",
            "limitation": "No independent field validation. Dataset-source shortcuts may produce confident errors.",
        },
    )
    with (output / "training_history.csv").open("w", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["model", "threshold", "f1", "pr_auc", "roc_auc"]
        )
        writer.writeheader()
        writer.writerows({k: row[k] for k in writer.fieldnames} for row in history)
    plots(y[test], probabilities, output / "plots")
    print("Final untouched test:", evaluation)


if __name__ == "__main__":
    main()

"""Evaluate a frozen checkpoint on a NEW external URL CSV, never for tuning."""

import argparse
import csv
import json
import joblib
from pathlib import Path
from app.analyzers.url.features import features
from ml.common.metrics import metrics, save_json

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    rows = list(csv.DictReader(a.data_dir.open(encoding="utf-8-sig")))
    model = joblib.load(a.checkpoint)
    registry = json.loads((a.checkpoint.parent / "registry.json").read_text())
    result = metrics(
        [int(r["label"]) for r in rows],
        model.predict_proba([features(r["url"]) for r in rows])[:, 1],
        registry["threshold"],
    )
    save_json(a.output_dir / "external_metrics.json", result)
    print(result)

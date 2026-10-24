import argparse
from pathlib import Path
import joblib
from ml.fusion_model.data import load
from ml.common.metrics import metrics, save_json

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    x, y, _, _ = load(a.data_dir)
    result = metrics(y, joblib.load(a.checkpoint).predict_proba(x)[:, 1])
    save_json(a.output_dir / "external_metrics.json", result)
    print(result)

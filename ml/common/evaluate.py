import argparse
import json
from pathlib import Path
from ml.common.data import read_manifest
from ml.common.inference import infer
from ml.common.metrics import metrics, save_json, plots


def main(modality):
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--split", choices=["test", "ood"], default="ood")
    a = p.parse_args()
    if a.output_dir.exists() and (a.output_dir / "external_metrics.json").exists():
        raise ValueError("Evaluation output already exists")
    rows = [r for r in read_manifest(a.data_dir) if r["split"] == a.split]
    if not rows:
        raise ValueError("No evaluation rows")
    results = [infer(a.data_dir / r["path"], a.checkpoint, modality) for r in rows]
    registry = json.loads((a.checkpoint.parent / "registry.json").read_text())
    y = [int(r["label"]) for r in rows]
    probabilities = [r["probability"] for r in results]
    result = metrics(y, probabilities, registry["threshold"])
    save_json(a.output_dir / "external_metrics.json", result)
    plots(y, probabilities, a.output_dir / "plots", registry["threshold"])
    print(result)

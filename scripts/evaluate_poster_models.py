"""Compare installed and candidate models on untouched TextRich commercial posters."""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.common.community_image import infer as community_infer
from ml.common.inference import infer as project_infer
from ml.common.metrics import metrics


ROOT = Path("datasets/external/textrich-commercial-posters")
OUTPUT = Path("research/experiments/image-poster-external")
MODELS = {
    "installed_community_v3": Path("models/image/community-forensics-384/model.safetensors"),
    "candidate_efficientnet_v4": Path("research/experiments/image-efficientnet-v4/best.pt"),
}


def main():
    rows = list(csv.DictReader((ROOT / "manifest.csv").open(encoding="utf-8")))
    if len(rows) != 100 or {int(r["label"]) for r in rows} != {0, 1}:
        raise ValueError("Expected the untouched balanced 100-poster manifest")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = {"dataset": json.loads((ROOT / "source.json").read_text(encoding="utf-8")), "models": {}}
    for name, checkpoint in MODELS.items():
        predictions = []
        for index, row in enumerate(rows, 1):
            path = ROOT / row["path"]
            result = community_infer(path, checkpoint) if name.startswith("installed") else project_infer(path, checkpoint, "image")
            predictions.append({"path": row["path"], "label": int(row["label"]),
                                "score": result["probability"], "verdict": result["verdict"],
                                "uncertainty": result["uncertainty"], "unstable": result["unstable"]})
            if index % 10 == 0:
                print(f"{name}: {index}/{len(rows)}", flush=True)
        threshold = json.loads(Path("models/image/registry.json").read_text())["threshold"] if name.startswith("installed") else json.loads((checkpoint.parent / "registry.json").read_text())["threshold"]
        y = [p["label"] for p in predictions]
        scores = [p["score"] for p in predictions]
        accepted = [p for p in predictions if p["verdict"] != "inconclusive"]
        result = {
            "threshold": threshold,
            "overall": metrics(y, scores, threshold),
            "accepted_count": len(accepted),
            "accepted_errors": sum((p["score"] >= threshold) != bool(p["label"]) for p in accepted),
            "synthetic_missed": sum(p["label"] == 1 and p["score"] < threshold for p in predictions),
            "real_false_alarms": sum(p["label"] == 0 and p["score"] >= threshold for p in predictions),
            "uncertainty_abstentions": len(predictions) - len(accepted),
            "limitations": "Only 50 real Crello subset posters and 50 GPT-Image-2 posters. Publisher data selection and upstream model pretraining overlap are not independently audited.",
        }
        (OUTPUT / f"{name}-predictions.json").write_text(json.dumps(predictions, indent=2), encoding="utf-8")
        summary["models"][name] = result
        (OUTPUT / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(name, json.dumps({k: result[k] for k in ("synthetic_missed", "real_false_alarms", "accepted_count", "accepted_errors")}), flush=True)


if __name__ == "__main__":
    main()

import json
from functools import lru_cache
from pathlib import Path
import joblib
from app.core.config import settings
from app.analyzers.url.features import features
from app.schemas.evidence import finding


def registry() -> list[dict]:
    records = []
    for name in ("url", "image", "audio", "video", "fusion"):
        path = settings.model_dir / name / "registry.json"
        if path.exists():
            try:
                record = json.loads(path.read_text())
                required = {"version", "architecture", "threshold", "file_path"}
                if not required.issubset(record):
                    raise ValueError("Incomplete registry metadata")
                artifact = (path.parent / record["file_path"]).resolve()
                if not artifact.is_relative_to(path.parent.resolve()):
                    raise ValueError("Model path leaves its registry directory")
                record["available"] = artifact.is_file()
                if not record["available"]:
                    record["reason"] = "Registered checkpoint file is missing"
                records.append(record | {"name": name})
            except (ValueError, KeyError):
                records.append(
                    {
                        "name": name,
                        "available": False,
                        "reason": "Invalid registry metadata",
                    }
                )
        else:
            records.append(
                {
                    "name": name,
                    "available": False,
                    "reason": "No trained checkpoint installed",
                }
            )
    return records


@lru_cache(maxsize=8)
def load_tabular(path: str, modified: int):
    return joblib.load(path)  # Trusted operator-installed model files only.


def predict_url(url: str, asset: str):
    record = next(x for x in registry() if x["name"] == "url")
    if not record["available"]:
        return finding(
            asset, "url_detector", "phishing", "unavailable", record["reason"]
        )
    path = settings.model_dir / "url" / record["file_path"]
    model = load_tabular(str(path), path.stat().st_mtime_ns)
    probability = float(model.predict_proba([features(url)])[0, 1])
    experimental = record.get("deployment_status") != "validated_external"
    confidence = max(0.05, 1 - 4 * probability * (1 - probability))
    if experimental:
        confidence = min(confidence, 0.35)
    return finding(
        asset,
        "url_detector",
        "phishing",
        "phishing_probability",
        "Experimental lexical classifier: raw probability is not validated field risk. Dataset-source shortcuts can cause false positives; manual verification is required."
        if experimental
        else "Calibrated URL lexical classifier; page content is evaluated separately.",
        probability,
        confidence,
        model_version=record["version"],
        hypothesis="phishing",
        metadata={
            "threshold": record["threshold"],
            "features": features(url),
            "deployment_status": record.get("deployment_status", "experimental"),
            "raw_model_probability": probability,
            "risk_eligible": not experimental,
        },
    )


def predict_media(path: Path, modality: str, asset: str):
    record = next(x for x in registry() if x["name"] == modality)
    if not record["available"]:
        return finding(
            asset,
            modality + "_detector",
            "synthetic_media",
            "unavailable",
            record["reason"],
        )
    try:
        checkpoint = settings.model_dir / modality / record["file_path"]
        if modality == "image" and record.get("runtime") == "huggingface_image":
            from ml.common.hf_image import infer

            result = infer(path, checkpoint)
        elif modality == "image" and record.get("runtime") == "community_forensics":
            from ml.common.community_image import infer

            result = infer(path, checkpoint)
        elif modality == "video" and record.get("runtime") == "huggingface_video":
            from ml.common.hf_video import infer

            result = infer(path, checkpoint)
        else:
            from ml.common.inference import infer

            result = infer(path, checkpoint, modality)
    except Exception as exc:
        return finding(
            asset,
            modality + "_detector",
            "synthetic_media",
            "unavailable",
            f"Model inference did not complete: {type(exc).__name__}: {str(exc)[:160]}",
            model_version=record["version"],
        )
    return finding(
        asset,
        modality + "_detector",
        "synthetic_media" if modality != "video" else "manipulation",
        "synthetic_probability",
        "Model estimate within its documented training domain; synthetic content is not necessarily malicious.",
        result["probability"],
        1 - result["uncertainty"],
        model_version=record["version"],
        hypothesis="synthetic_media",
        metadata=result | {
            "architecture": record["architecture"],
            "threshold": record["threshold"],
            "calibration": result.get("calibration", record.get("calibration", "none")),
            "deployment_status": record.get("deployment_status", "experimental"),
            "limitations": record.get("limitation") or result.get("limitations", "Dataset-specific model; real-world accuracy is not established."),
            "test_metrics": record.get("test_metrics"),
            "poster_external_metrics": record.get("poster_external_metrics"),
        },
    )

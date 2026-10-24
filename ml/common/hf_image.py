"""Offline-only inference with an operator-installed safetensors checkpoint."""

from functools import lru_cache
from pathlib import Path
import io
from PIL import Image, ImageOps
import torch


@lru_cache(maxsize=2)
def load(directory: str, modified: int):
    from transformers import AutoImageProcessor, AutoModelForImageClassification

    processor = AutoImageProcessor.from_pretrained(
        directory, local_files_only=True, trust_remote_code=False, use_fast=False
    )
    model = AutoModelForImageClassification.from_pretrained(
        directory, local_files_only=True, trust_remote_code=False, use_safetensors=True
    )
    model.eval()
    labels = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    ai = [
        key
        for key, value in labels.items()
        if value in ("ai", "artificial", "fake", "synthetic")
    ]
    if len(ai) != 1 or len(labels) != 2:
        raise ValueError("Unrecognized AI/human class mapping")
    return processor, model, ai[0]


def infer(path: Path, checkpoint: Path):
    processor, model, ai_index = load(
        str(checkpoint.parent), checkpoint.stat().st_mtime_ns
    )
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    # Preserve the original prediction; transformations test stability, not truth.
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    with Image.open(io.BytesIO(buffer.getvalue())) as compressed:
        views = [("Original image", image), ("Horizontal flip", ImageOps.mirror(image)), ("JPEG quality 85", compressed.convert("RGB"))]
    scores = []
    with torch.inference_mode():
        for name, view in views:
            inputs = processor(images=view, return_tensors="pt")
            score = float(torch.softmax(model(**inputs).logits, dim=-1)[0, ai_index])
            scores.append({"name": name, "score": score})
    probability = scores[0]["score"]
    spread = max(s["score"] for s in scores) - min(s["score"] for s in scores)
    return {
        "probability": probability,
        "bona_fide_probability": 1 - probability,
        "uncertainty": max(0.85 if spread >= 0.25 else 0.65, 4 * probability * (1 - probability)),
        "stability_checks": scores,
        "score_spread": spread,
        "unstable": spread >= 0.25,
        "explanation_method": "Transformation sensitivity; not localization or proof of AI generation.",
        "ood": "not_evaluated",
        "calibration": "uncalibrated",
        "deployment_status": "experimental",
        "limitations": "Publisher reports overfitting; no independent validation here. Certificates, screenshots, composites and unseen generators may be misclassified.",
    }

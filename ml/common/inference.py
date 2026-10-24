from functools import lru_cache
from pathlib import Path
import os
import io
import numpy as np
import torch
from PIL import Image, ImageOps
from ml.common.model import Detector
from ml.common.media import image_tensor, audio_chunks, face_frames


@lru_cache(maxsize=4)
def load(path, modified):
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    config = checkpoint["config"]
    model = Detector(config["modality"], config["architecture"], pretrained=False)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model, checkpoint


def infer(path: Path, checkpoint_path: Path, modality: str):
    model, checkpoint = load(str(checkpoint_path), checkpoint_path.stat().st_mtime_ns)
    if checkpoint["config"]["modality"] != modality:
        raise ValueError("Checkpoint modality mismatch")
    if modality == "audio":
        chunks = audio_chunks(path)
    elif modality == "video":
        frames = face_frames(path)
        if not frames:
            raise ValueError(
                "No detectable faces; visual deepfake inference is unknown"
            )
        chunks = [
            (image_tensor(image), float(time), float(time) + 0.1)
            for image, time in frames
        ]
    else:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            with Image.open(io.BytesIO(buffer.getvalue())) as jpeg:
                views = [image, ImageOps.mirror(image), jpeg.copy()]
            chunks = [(image_tensor(view), 0.0, 0.0) for view in views]
    probabilities = []
    distances = []
    with torch.inference_mode():
        for start in range(0, len(chunks), 16):
            batch = torch.stack([c[0] for c in chunks[start : start + 16]])
            logits, embeddings = model(batch)
            probabilities.extend(
                torch.sigmoid(logits / checkpoint["temperature"]).tolist()
            )
            values = embeddings.numpy()
            distances.extend(
                np.mean(
                    (values - np.array(checkpoint["ood_mean"])) ** 2
                    / np.array(checkpoint["ood_variance"]),
                    axis=1,
                ).tolist()
            )
    # Preserve the calibrated original prediction; perturbations are diagnostics.
    probability = float(probabilities[0] if modality == "image" else np.mean(probabilities))
    spread = float(max(probabilities) - min(probabilities))
    threshold = checkpoint.get("threshold", 0.5)
    class_changed = modality == "image" and len({p >= threshold for p in probabilities}) > 1
    unstable = modality == "image" and (spread >= 0.25 or class_changed)
    ood = bool(max(distances) > checkpoint["ood_threshold"])
    uncertainty = max(
        4 * probability * (1 - probability),
        float(np.std(probabilities)),
        0.9 if ood else 0,
        0.75 if unstable else 0,
    )
    return {
        "probability": probability,
        "calibration": checkpoint.get("calibration", "temperature_scaling"),
        "temperature": checkpoint["temperature"],
        "threshold": checkpoint.get("threshold", 0.5),
        "predicted_class": "ai_generated" if probability >= checkpoint.get("threshold", 0.5) else "real",
        "verdict": "inconclusive" if uncertainty >= 0.65 else "likely_ai_generated" if probability >= checkpoint.get("threshold", 0.5) else "likely_real",
        "confidence_method": "1 - max(4p(1-p), segment variability, OOD floor, transformation-instability floor); heuristic, not measured correctness probability",
        "bona_fide_probability": 1 - probability,
        "uncertainty": min(1, uncertainty),
        "ood": "possibly_out_of_distribution" if ood else "in_distribution",
        "ood_distance": max(distances),
        "ood_threshold": checkpoint["ood_threshold"],
        "aggregation": "original_image" if modality == "image" else "mean",
        "unstable": unstable,
        "stability_class_changed": class_changed,
        "stability_reasons": (["class_changed"] if class_changed else []) + (["score_spread"] if modality == "image" and spread >= 0.25 else []),
        "stability_range": spread if modality == "image" else None,
        "stability_checks": [{"name": name, "score": p} for name, p in zip(["Original image", "Horizontal flip", "JPEG quality 85"], probabilities)] if modality == "image" else [],
        "segments": [
            {"start": c[1], "end": c[2], "probability": p}
            for c, p in zip(chunks, probabilities)
        ]
        if modality != "image"
        else [],
    }

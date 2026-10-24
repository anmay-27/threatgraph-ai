from pathlib import Path
import numpy as np
import soundfile as sf
from app.schemas.evidence import finding
from app.services.registry import predict_media


def inspect_audio(path: Path, asset: str):
    info = sf.info(path)
    if info.duration > 600:
        raise ValueError("Audio exceeds 10 minute processing limit")
    samples, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = samples.mean(axis=1)
    waveform = [
        float(np.max(np.abs(x)))
        for x in np.array_split(mono, min(120, len(mono)))
        if len(x)
    ]
    metadata = {
        "duration": info.duration,
        "sample_rate": rate,
        "channels": info.channels,
        "waveform": waveform,
    }
    return metadata, [
        finding(
            asset,
            "audio_inspector",
            "metadata",
            "audio_metadata",
            "Decoded audio metadata and peak waveform.",
            metadata=metadata,
        ),
        predict_media(path, "audio", asset),
    ]

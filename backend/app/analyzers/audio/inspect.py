from pathlib import Path
import numpy as np
import soundfile as sf
from app.schemas.evidence import finding
from app.services.registry import predict_media


def inspect_audio(path: Path, asset: str):
    info = sf.info(path)
    if info.duration > 600:
        raise ValueError("Audio exceeds 10 minute processing limit")
    if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
        raise ValueError("Audio contains no decodable samples")
    if info.channels > 32:
        raise ValueError("Audio exceeds the 32-channel inspection limit")
    # Read bounded blocks instead of allocating the entire decoded recording.
    waveform = np.zeros(min(120, info.frames), dtype=np.float32)
    offset = 0
    with sf.SoundFile(path) as stream:
        for block in stream.blocks(blocksize=16384, dtype="float32", always_2d=True):
            if not np.isfinite(block).all():
                raise ValueError("Audio contains non-finite samples")
            peaks = np.max(np.abs(block), axis=1)
            bins = np.minimum((np.arange(offset, offset + len(block)) * len(waveform)) // info.frames, len(waveform)-1)
            np.maximum.at(waveform, bins, peaks)
            offset += len(block)
    waveform = waveform.tolist()
    metadata = {
        "duration": info.duration,
        "sample_rate": info.samplerate,
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

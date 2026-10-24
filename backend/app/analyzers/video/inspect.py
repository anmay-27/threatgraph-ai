import shutil
import subprocess
import tempfile
from pathlib import Path
import cv2
from app.schemas.evidence import finding
from app.services.registry import predict_media
from app.analyzers.image.inspect import decode_qr
from app.analyzers.audio.inspect import inspect_audio


def inspect_video(path: Path, asset: str):
    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not capture.isOpened() or fps <= 0 or frames <= 0:
            raise ValueError("Video could not be decoded")
        duration = frames / fps
        if duration > 600:
            raise ValueError("Video exceeds 10 minute processing limit")
        urls = []
        for index in range(0, int(frames), max(1, int(frames / 24))):
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if ok:
                if max(frame.shape[:2]) > 1800:
                    frame = cv2.resize(
                        frame,
                        (0, 0),
                        fx=1800 / max(frame.shape[:2]),
                        fy=1800 / max(frame.shape[:2]),
                    )
                urls.extend(decode_qr(frame))
        metadata = {"duration": duration, "fps": fps, "frames": frames}
    finally:
        capture.release()
    evidence = [
        finding(
            asset,
            "video_inspector",
            "metadata",
            "video_metadata",
            "Video was sampled at up to 24 positions; unsampled content may be missed.",
            metadata=metadata,
        ),
        predict_media(path, "video", asset),
    ]
    if shutil.which("ffmpeg"):
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "audio.wav"
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    str(path),
                    "-vn",
                    "-t",
                    "600",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(audio),
                ],
                capture_output=True,
                timeout=45,
            )
            if result.returncode == 0:
                _, audio_evidence = inspect_audio(audio, asset)
                evidence.extend(audio_evidence)
            else:
                evidence.append(
                    finding(
                        asset,
                        "audio_extraction",
                        "metadata",
                        "no_audio_decoded",
                        "No audio stream could be decoded.",
                    )
                )
    else:
        evidence.append(
            finding(
                asset,
                "audio_extraction",
                "metadata",
                "unavailable",
                "FFmpeg is not installed.",
            )
        )
    return metadata, evidence, list(dict.fromkeys(urls))

"""Offline temporal screening with a pinned VideoMAE checkpoint.

Whole-frame uniform sampling follows the publisher's preprocessing. Face detection
is a domain gate only, never an authenticity detector or a replacement crop.
"""
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image


def sample_video(path: Path):
    capture = cv2.VideoCapture(str(path))
    faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    frames, timestamps, face_count = [], [], 0
    try:
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not capture.isOpened() or not np.isfinite(fps) or fps <= 0 or count < 16 or count / fps > 600:
            raise ValueError('Need a decodable video with at least 16 frames and duration <=10 minutes')
        for index in np.linspace(0, count - 1, 16, dtype=int):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
            ok, frame = capture.read()
            if not ok:
                raise ValueError('A sampled video frame could not be decoded')
            # Bound working memory while retaining enough resolution for preprocessing.
            scale = min(1, 960 / max(frame.shape[:2]))
            frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            face_count += int(len(faces.detectMultiScale(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(40,40))) > 0)
            frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            timestamps.append(float(index / fps))
        if face_count < 8:
            raise ValueError(f'Faces detected in only {face_count}/16 sampled frames; insufficient facial-video coverage for this model')
        return frames, timestamps, count / fps, face_count
    finally:
        capture.release()


@lru_cache(maxsize=1)
def load(path: str, modified: int):
    from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor
    torch.set_num_threads(4)
    directory = str(Path(path).parent)
    processor = VideoMAEImageProcessor.from_pretrained(directory, local_files_only=True)
    model = VideoMAEForVideoClassification.from_pretrained(directory, local_files_only=True, use_safetensors=True)
    if model.config.num_frames != 16 or model.config.id2label != {0: 'real', 1: 'fake'}:
        raise ValueError('Unexpected video model sampling or label mapping')
    model.eval()
    return processor, model


def infer(path: Path, checkpoint: Path):
    frames, timestamps, duration, face_count = sample_video(path)
    processor, model = load(str(checkpoint), checkpoint.stat().st_mtime_ns)
    with torch.inference_mode():
        inputs = processor(frames, return_tensors='pt')
        probability = float(torch.softmax(model(**inputs).logits, dim=-1)[0, 1])
    if not np.isfinite(probability):
        raise ValueError('Video model returned a non-finite score')
    return {
        'probability': probability, 'bona_fide_probability': 1-probability,
        'threshold': .5, 'predicted_class': 'manipulated' if probability >= .5 else 'real',
        'verdict': 'inconclusive', 'uncertainty': max(.75, 4*probability*(1-probability)),
        'confidence_method': 'Conservative research ceiling; not measured correctness probability',
        'calibration': 'none', 'risk_eligible': False, 'ood': 'not_estimated',
        'aggregation': 'single_temporal_clip', 'sampled_frames': 16,
        'face_frames': face_count, 'sample_timestamps': timestamps, 'duration': duration,
        'segments': [],
        'limitations': 'Uncalibrated third-party FaceForensics++ subset model. No independent video benchmark has been run here. Sixteen whole frames are sampled across the video; unsampled alterations and unseen generators can be missed. The score does not locate an altered frame or verify audio.',
    }

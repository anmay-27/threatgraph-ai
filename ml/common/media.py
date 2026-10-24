"""Shared deterministic preprocessing for training and deployed inference."""

import io
import random
from pathlib import Path
import cv2
import numpy as np
import soundfile as sf
import torch
from PIL import Image, ImageFilter, ImageOps
from scipy.signal import resample_poly
from torchvision import transforms


def image_tensor(image: Image.Image, augment=False):
    image = ImageOps.exif_transpose(image).convert("RGB")
    if augment:
        if random.random() < 0.5:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=random.randint(45, 95))
            image = Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")
        if random.random() < 0.3:
            image = image.filter(ImageFilter.GaussianBlur(random.uniform(0.2, 1.2)))
    pipeline = [transforms.Resize((256, 256))]
    pipeline += (
        [
            transforms.RandomResizedCrop(224, scale=(0.7, 1)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(0.1, 0.1, 0.1, 0.02),
        ]
        if augment
        else [transforms.CenterCrop(224)]
    )
    pipeline += [
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
    return transforms.Compose(pipeline)(image)


def audio_chunks(path: Path, augment=False):
    import librosa

    samples, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = samples.mean(axis=1)
    if len(mono) / rate > 600:
        raise ValueError("Audio exceeds processing duration")
    divisor = np.gcd(rate, 16000)
    mono = resample_poly(mono, 16000 // divisor, rate // divisor)
    mono /= max(float(np.max(np.abs(mono))), 1e-6)
    if augment:
        mono += np.random.normal(0, random.uniform(0, 0.015), mono.shape).astype(
            np.float32
        )
        if random.random() < 0.3:
            mono = resample_poly(resample_poly(mono, 1, 2), 2, 1)
        if random.random() < 0.3:
            mono = np.round(mono * 127) / 127
    result = []
    for start in range(0, len(mono), 64000):
        chunk = mono[start : start + 64000]
        padded = np.pad(chunk, (0, 64000 - len(chunk)))
        mel = librosa.feature.melspectrogram(
            y=padded, sr=16000, n_fft=512, hop_length=160, n_mels=64
        )
        logmel = librosa.power_to_db(mel, ref=np.max)
        tensor = torch.tensor((logmel + 40) / 40, dtype=torch.float32).unsqueeze(0)
        result.append((tensor, start / 16000, min(start + 64000, len(mono)) / 16000))
    if not result:
        raise ValueError("Empty audio")
    return result


def face_frames(path: Path, limit=24):
    capture = cv2.VideoCapture(str(path))
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    result = []
    try:
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or count <= 0 or count / fps > 600:
            raise ValueError("Video invalid or exceeds duration limit")
        for frame_no in np.linspace(0, count - 1, min(limit, count), dtype=int):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_no))
            ok, frame = capture.read()
            if not ok:
                continue
            scale = min(1, 960 / max(frame.shape[:2]))
            frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
            # Largest face baseline. No-face is unknown, never authentic by default.
            if len(faces):
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                margin = int(0.15 * w)
                crop = frame[
                    max(0, y - margin) : y + h + margin,
                    max(0, x - margin) : x + w + margin,
                ]
                result.append(
                    (
                        Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)),
                        frame_no / fps,
                    )
                )
    finally:
        capture.release()
    return result

"""Offline adapter for the official MIT Community Forensics ViT-small checkpoint.

Architecture and evaluation preprocessing follow JeongsooP/Community-Forensics
commit ee5b71d43db0f3779e1edd64ee927b13f2dd6ad4. No upstream Python executes.
"""
from functools import lru_cache
import io
import json
from pathlib import Path
import math
import torch
from PIL import Image, ImageOps
from torchvision import transforms


def image_tensor(image):
    return transforms.Compose([
        transforms.Resize(440), transforms.CenterCrop(384), transforms.ToTensor(),
        transforms.Normalize([.485,.456,.406], [.229,.224,.225]),
    ])(ImageOps.exif_transpose(image).convert('RGB'))


@lru_cache(maxsize=1)
def load(path: str, modified: int):
    import timm
    from safetensors.torch import load_file
    config = json.loads(Path(path).with_name('config.json').read_text())
    if (config.get('model_size'), config.get('input_size'), config.get('patch_size')) != ('small',384,16):
        raise ValueError('Unexpected Community Forensics architecture')
    torch.set_num_threads(4)
    model = torch.nn.Module()
    model.vit = timm.create_model('vit_small_patch16_384.augreg_in21k_ft_in1k', pretrained=False, num_classes=1)
    model.load_state_dict(load_file(path, device='cpu'), strict=True)
    model.eval()
    return model.vit


def assess_scores(scores, threshold):
    if not scores or not all(math.isfinite(p) and 0 <= p <= 1 for p in scores):
        raise ValueError('Non-finite or invalid classifier probability')
    p = scores[0]
    spread = max(scores)-min(scores)
    changed = len({s >= threshold for s in scores}) > 1
    unstable = changed or spread >= .25
    uncertainty = max(4*p*(1-p), .75 if unstable else 0)
    return dict(probability=p, bona_fide_probability=1-p, threshold=threshold,
                predicted_class='ai_generated' if p >= threshold else 'real',
                verdict='inconclusive' if uncertainty >= .65 else 'likely_ai_generated' if p >= threshold else 'likely_real',
                uncertainty=uncertainty, unstable=unstable, stability_class_changed=changed,
                stability_range=spread, stability_reasons=(['class_changed'] if changed else []) + (['score_spread'] if spread >= .25 else []),
                stability_checks=[dict(name=n, score=s) for n,s in zip(['Original image','Horizontal flip','JPEG quality 85'], scores)],
                confidence_method='1 - max(4p(1-p), transformation-instability floor); heuristic, not measured correctness probability',
                ood='not_estimated', aggregation='original_image', segments=[], calibration='temperature_scaling')


def infer(path: Path, checkpoint: Path):
    calibration = json.loads(checkpoint.with_name('calibration.json').read_text())
    temperature, threshold = calibration['temperature'], calibration['threshold']
    if not math.isfinite(temperature) or temperature <= 0 or not 0 < threshold <= 1:
        raise ValueError('Invalid calibration parameters')
    model = load(str(checkpoint), checkpoint.stat().st_mtime_ns)
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=85)
    with Image.open(io.BytesIO(buffer.getvalue())) as jpeg:
        views = [image, ImageOps.mirror(image), jpeg.convert('RGB')]
    with torch.inference_mode():
        scores = [float(torch.sigmoid(model(image_tensor(view).unsqueeze(0)).reshape(-1)[0] / temperature)) for view in views]
    return assess_scores(scores, threshold) | dict(temperature=temperature, pretrained_source='OwensLab/commfor-model-384', calibration_partition=calibration['partition'], limitations='Third-party pretrained vision model with local temperature calibration. Possible pretraining overlap with benchmark images; independent field reliability is not established. No altered-pixel localization or validated out-of-domain detector.')

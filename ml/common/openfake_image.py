"""Offline ONNX inference using the pinned publisher's preprocessing and cutoff."""
from functools import lru_cache
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageOps


@lru_cache(maxsize=1)
def load(path, modified):
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    return ort.InferenceSession(path, sess_options=options, providers=['CPUExecutionProvider'])


def tensor(image, shortest=440):
    width, height = image.size
    size = (shortest, int(shortest*height/width)) if width < height else (int(shortest*width/height), shortest)
    image = image.resize(size, Image.Resampling.BILINEAR)
    x, y = round((image.width-384)/2), round((image.height-384)/2)
    pixels = np.asarray(image.crop((x,y,x+384,y+384)), dtype=np.float32)/255.
    pixels = (pixels-np.array([.485,.456,.406],dtype=np.float32))/np.array([.229,.224,.225],dtype=np.float32)
    return np.transpose(pixels,(2,0,1))[None].copy()


def infer(path: Path, checkpoint: Path):
    session = load(str(checkpoint), checkpoint.stat().st_mtime_ns)
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
    scores = []
    def score(size):
        logit = float(session.run(None, {'pixel_values':tensor(image,size)})[0].reshape(-1)[0])
        if not math.isfinite(logit):raise ValueError('Nonfinite detector output')
        p = 1/(1+math.exp(-max(-50.,min(50.,.552*logit+.1933))))
        scores.append(dict(shortest_edge=size, logit=logit, score=p))
        return p
    primary = score(440)
    if .5 <= primary < .95:
        score(576);score(768)
    p = max(s['score'] for s in scores)
    verdict = 'likely_ai_generated' if p >= .95 else 'likely_real' if p <= .2 else 'inconclusive'
    return dict(probability=p,bona_fide_probability=1-p,threshold=.95,predicted_class='ai_generated' if p>=.95 else 'real',verdict=verdict,uncertainty=max(4*p*(1-p),.75 if verdict=='inconclusive' else 0),calibration='publisher_platt_scaling',deployment_status='experimental',ood='not_estimated',crop_checks=scores,aggregation='Publisher rule: rescore at 576/768 when primary score is between 0.5 and 0.95; maximum scaled score',limitations='OpenFake pretrained research detector, noncommercial weights. Publisher Platt scaling/cutoff; not locally calibrated or proof of origin. Low scores can miss AI edits. Scores on crop scales are not independent votes.')

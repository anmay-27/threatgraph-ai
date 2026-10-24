"""Runtime smoke test, explicitly NOT a video accuracy evaluation."""
import json
from pathlib import Path
import cv2
from ml.common.hf_video import infer

def main():
    image = cv2.imread('datasets/demo/astronaut.png')
    if image is None:
        raise ValueError('Missing scikit-image astronaut fixture')
    path = Path('datasets/demo/astronaut-motion.avi')
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 8, (512,512))
    if not writer.isOpened():
        raise ValueError('Video writer unavailable')
    try:
        for i in range(32):
            # Small deterministic translation of a still photograph.
            import numpy as np
            writer.write(cv2.warpAffine(image, np.float32([[1,0,i%4],[0,1,0]]), (512,512)))
    finally:
        writer.release()
    checkpoint = Path('models/video/videomae-ffpp/model.safetensors')
    result = infer(path, checkpoint)
    assert result['sampled_frames'] == 16 and 0 <= result['probability'] <= 1
    audit = {'fixture': str(path), 'fixture_source': 'https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/data/astronaut.png', 'purpose': 'Decoder, face-domain gate and real checkpoint execution only; translated still image is not a labelled deepfake benchmark', 'result': result}
    Path('research/results/video-runtime-smoke.json').write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2), flush=True)

if __name__ == '__main__':
    main()

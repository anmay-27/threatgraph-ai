import numpy as np
import soundfile as sf
import pytest
from app.analyzers.audio.inspect import inspect_audio


def test_audio_stereo_peaks_do_not_cancel(tmp_path):
    path = tmp_path / 'stereo.wav'
    samples = np.tile([.5, -.5], (32000, 1))
    sf.write(path, samples, 16000)
    metadata, evidence = inspect_audio(path, 'audio')
    assert len(metadata['waveform']) == 120
    assert max(metadata['waveform']) == pytest.approx(.5)
    assert metadata['duration'] == 2
    assert any(e.label == 'unavailable' and e.source == 'audio_detector' for e in evidence)


def test_empty_audio_has_clear_failure(tmp_path):
    path = tmp_path / 'empty.wav'
    sf.write(path, np.zeros(0), 16000)
    with pytest.raises(ValueError, match='no decodable samples'):
        inspect_audio(path, 'audio')


def test_nonfinite_audio_rejected(tmp_path):
    path = tmp_path / 'invalid.wav'
    sf.write(path, np.array([np.nan, .5]), 16000, subtype='FLOAT')
    with pytest.raises(ValueError, match='non-finite'):
        inspect_audio(path, 'audio')


def test_video_qr_sampling_is_bounded(monkeypatch, tmp_path):
    from app.analyzers.video import inspect as module
    import cv2
    positions = []
    class Capture:
        def get(self, key):
            return 24 if key == cv2.CAP_PROP_FPS else 47
        def isOpened(self): return True
        def set(self, key, value): positions.append(value)
        def read(self): return True, np.zeros((16,16,3), dtype=np.uint8)
        def release(self): pass
    monkeypatch.setattr(module.cv2, 'VideoCapture', lambda _: Capture())
    monkeypatch.setattr(module, 'decode_qr', lambda _: [])
    monkeypatch.setattr(module, 'predict_media', lambda *args: None)
    monkeypatch.setattr(module.shutil, 'which', lambda _: None)
    module.inspect_video(tmp_path/'fixture.avi', 'video')
    assert len(positions) == 24
    assert positions[0] == 0 and positions[-1] == 46

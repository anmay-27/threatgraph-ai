from pathlib import Path
from types import SimpleNamespace
import pytest
import torch
from PIL import Image
from ml.common import hf_video


def test_nonfacial_video_abstains():
    with pytest.raises(ValueError, match='insufficient facial-video coverage'):
        hf_video.sample_video(Path('datasets/demo/shapes.avi'))


def test_temporal_score_keeps_uncalibrated_status(monkeypatch, tmp_path):
    checkpoint = tmp_path / 'model.safetensors'
    checkpoint.touch()
    frames = [Image.new('RGB', (224,224)) for _ in range(16)]
    monkeypatch.setattr(hf_video, 'sample_video', lambda p: (frames, list(range(16)), 16, 16))
    def processor(inputs, **kwargs):
        assert len(inputs) == 16
        return {'pixel_values': torch.zeros((1,16,3,224,224))}
    def model(**kwargs):
        assert kwargs['pixel_values'].shape[1] == 16
        return SimpleNamespace(logits=torch.tensor([[0., 5.]]))
    monkeypatch.setattr(hf_video, 'load', lambda *args: (processor, model))
    result = hf_video.infer(tmp_path / 'clip.mp4', checkpoint)
    assert result['probability'] > .99
    assert result['verdict'] == 'inconclusive'
    assert result['risk_eligible'] is False
    assert result['segments'] == []  # No invented per-frame predictions.


def test_video_registry_routes_temporal_adapter(monkeypatch, tmp_path):
    import app.services.registry as registry
    monkeypatch.setattr(registry, 'registry', lambda: [dict(name='video', available=True, runtime='huggingface_video', file_path='model.safetensors', version='test', architecture='videomae', threshold=.5)])
    monkeypatch.setattr(hf_video, 'infer', lambda *args: dict(probability=.9, uncertainty=.75, calibration='none', risk_eligible=False))
    result = registry.predict_media(tmp_path / 'clip.mp4', 'video', 'asset')
    assert result.label == 'synthetic_probability'
    assert result.category == 'manipulation'
    assert result.confidence == .25
    assert result.metadata['risk_eligible'] is False

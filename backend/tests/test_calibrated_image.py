"""Inference contract tests; synthetic tensors are never accuracy measurements."""
import numpy as np
import pytest
from PIL import Image


@pytest.mark.parametrize('probability,distance,expected', [(.99, 0, 'likely_ai_generated'), (.01, 0, 'likely_real'), (.5, 0, 'inconclusive'), (.99, 10, 'inconclusive')])
def test_calibrated_inference_preserves_prediction_and_abstains(monkeypatch, tmp_path, probability, distance, expected):
    torch = pytest.importorskip('torch')
    from ml.common import inference
    class Model:
        def __call__(self, batch):
            return torch.full((len(batch),), float(np.log(probability / (1-probability)))), torch.full((len(batch), 1), float(distance))
    checkpoint = dict(config={'modality': 'image'}, temperature=1., threshold=.6, ood_mean=[0.], ood_variance=[1.], ood_threshold=2., calibration='temperature_scaling')
    monkeypatch.setattr(inference, 'load', lambda *args: (Model(), checkpoint))
    artifact = tmp_path / 'model.pt'
    artifact.touch()
    path = tmp_path / 'image.png'
    Image.new('RGB', (32, 32), 'blue').save(path)
    result = inference.infer(path, artifact, 'image')
    assert result['probability'] == pytest.approx(probability)
    assert result['verdict'] == expected
    assert result['threshold'] == .6
    assert result['calibration'] == 'temperature_scaling'
    assert len(result['stability_checks']) == 3
    if distance:
        assert result['ood'] == 'possibly_out_of_distribution'
        assert result['uncertainty'] >= .9


def test_small_transformation_class_change_triggers_abstention(monkeypatch, tmp_path):
    torch = pytest.importorskip('torch')
    from ml.common import inference
    class Model:
        def __call__(self, batch):
            p = torch.tensor([.1, .31, .1])
            return torch.logit(p), torch.zeros((3, 1))
    checkpoint = dict(config={'modality': 'image'}, temperature=1., threshold=.3, ood_mean=[0.], ood_variance=[1.], ood_threshold=2.)
    monkeypatch.setattr(inference, 'load', lambda *args: (Model(), checkpoint))
    artifact = tmp_path / 'model.pt'
    artifact.touch()
    path = tmp_path / 'image.png'
    Image.new('RGB', (32, 32), 'blue').save(path)
    result = inference.infer(path, artifact, 'image')
    assert result['probability'] == pytest.approx(.1)
    assert result['predicted_class'] == 'real'
    assert result['stability_range'] < .25
    assert result['stability_reasons'] == ['class_changed']
    assert result['unstable'] is True
    assert result['verdict'] == 'inconclusive'

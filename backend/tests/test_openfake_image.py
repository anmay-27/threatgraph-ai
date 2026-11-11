import math
import numpy as np
from PIL import Image
from ml.common import openfake_image


class Scores:
    def __init__(self, probabilities):
        self.values=iter(probabilities)
        self.calls=0
    def run(self, _, inputs):
        self.calls+=1
        assert inputs['pixel_values'].shape == (1,3,384,384)
        p=next(self.values)
        return [np.array([[(math.log(p/(1-p))-.1933)/.552]],dtype=np.float32)]


def run(monkeypatch,tmp_path, probabilities):
    session=Scores(probabilities)
    monkeypatch.setattr(openfake_image,'load',lambda *args:session)
    path=tmp_path/'input.png';Image.new('RGB',(500,900),'gray').save(path)
    checkpoint=tmp_path/'model.onnx';checkpoint.touch()
    return openfake_image.infer(path,checkpoint),session


def test_secondary_crops_use_publisher_rule(monkeypatch,tmp_path):
    result,session=run(monkeypatch,tmp_path,[.7,.97,.8])
    assert session.calls==3
    assert abs(result['probability']-.97)<1e-6
    assert result['verdict']=='likely_ai_generated'


def test_below_cutoff_is_not_automatically_authentic(monkeypatch,tmp_path):
    result,session=run(monkeypatch,tmp_path,[.9,.88,.91])
    assert result['verdict']=='inconclusive'
    assert result['uncertainty']>=.75


def test_low_primary_does_not_search_crops_for_highest_score(monkeypatch,tmp_path):
    result,session=run(monkeypatch,tmp_path,[.1])
    assert session.calls==1
    assert result['verdict']=='likely_real'

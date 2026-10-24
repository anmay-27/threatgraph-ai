import numpy as np
import pytest
from ml.common.community_image import assess_scores
from scripts.evaluate_community_candidate import calibrate, sigmoid
from ml.common.metrics import metrics


def test_small_threshold_crossing_abstains_and_preserves_original():
    result = assess_scores([.89,.91,.9],.9)
    assert result['probability'] == .89
    assert result['predicted_class'] == 'real'
    assert result['stability_class_changed'] is True
    assert result['verdict'] == 'inconclusive'
    assert result['uncertainty'] >= .75


def test_invalid_score_cannot_become_prediction():
    with pytest.raises(ValueError):
        assess_scores([float('nan'),.8,.8],.5)


def test_calibration_obeys_fixed_false_positive_constraint():
    labels = np.array([0]*10+[1]*10)
    logits = np.array([-4,-3,-2,-1,0,.1,.2,.3,.5,1,-2,-1,.2,.8,1,2,3,4,5,6])
    fitted = calibrate(labels,logits)
    measured = metrics(labels,sigmoid(logits,fitted['temperature']),fitted['threshold'])
    assert measured['false_positive_rate'] <= .2
    assert measured['recall'] > 0


def test_adapter_routes_without_reinterpreting_class_mapping(monkeypatch,tmp_path):
    import app.services.registry as registry
    import ml.common.community_image as adapter
    monkeypatch.setattr(registry,'registry',lambda:[dict(name='image',available=True,runtime='community_forensics',file_path='candidate/model.safetensors',version='v3-test',architecture='vit',threshold=.6)])
    monkeypatch.setattr(registry.settings,'model_dir',tmp_path)
    def infer(path,checkpoint):
        assert checkpoint == tmp_path/'image/candidate/model.safetensors'
        return assess_scores([.95,.94,.96],.6)
    monkeypatch.setattr(adapter,'infer',infer)
    result = registry.predict_media(tmp_path/'image.png','image','asset')
    assert result.score == .95
    assert result.metadata['predicted_class'] == 'ai_generated'
    assert result.category == 'synthetic_media'

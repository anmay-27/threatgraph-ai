import numpy as np
from ml.common.metrics import metrics
from app.fusion.features import vector, SOURCES
from app.schemas.evidence import finding


def test_missing_modality_is_masked():
    row = vector([], [])
    assert row[0] == 0.5 and row[1] == 0 and row[2] == 1
    evidence = [
        finding("asset", "url_detector", "phishing", "prediction", "test", 0.9, 0.8)
    ]
    row = vector(evidence, [])
    assert np.isclose(row[0], 0.9) and row[1] == 1
    assert len(row) == len(SOURCES) * 3 + 2


def test_metrics_count_probability_one_in_calibration():
    result = metrics([0, 1], [0, 1])
    assert result["ece"] == 0 and result["f1"] == 1
    wrong = metrics([0, 0], [1, 1])
    assert wrong["ece"] == 1 and wrong["roc_auc"] is None

from pathlib import Path
import pytest
from app.core.config import settings
from app.services.registry import predict_url


def test_installed_genuine_url_checkpoint(monkeypatch):
    if not Path("models/url/best.joblib").exists():
        pytest.skip("Train or install the URL checkpoint first")
    monkeypatch.setattr(settings, "model_dir", Path("models"))
    result = predict_url("https://example.com/", "test")
    assert result.label == "phishing_probability"
    assert 0 <= result.score <= 1
    assert result.model_version != "rules-1.0"
    assert len(result.metadata["features"]) == 17
    assert result.confidence <= 0.35 and result.uncertainty >= 0.65

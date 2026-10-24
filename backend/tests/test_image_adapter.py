from app.services.registry import predict_media


def test_hf_adapter_routes_local_checkpoint_and_preserves_uncertainty(
    monkeypatch, tmp_path
):
    import app.services.registry as registry
    import ml.common.hf_image as adapter

    monkeypatch.setattr(
        registry,
        "registry",
        lambda: [
            {
                "name": "image",
                "available": True,
                "runtime": "huggingface_image",
                "file_path": "model.safetensors",
                "version": "experimental",
                "architecture": "siglip",
                "threshold": 0.8,
            }
        ],
    )
    monkeypatch.setattr(registry.settings, "model_dir", tmp_path)

    def infer(image, checkpoint):
        assert checkpoint == tmp_path / "image" / "model.safetensors"
        return {"probability": 0.98, "uncertainty": 0.65, "calibration": "uncalibrated"}

    monkeypatch.setattr(adapter, "infer", infer)
    evidence = predict_media(tmp_path / "input.jpg", "image", "root")
    assert evidence.score == 0.98
    assert evidence.confidence <= 0.35
    assert evidence.metadata["calibration"] == "uncalibrated"


def test_hf_failure_returns_unavailable_not_a_prediction(monkeypatch, tmp_path):
    import app.services.registry as registry
    import ml.common.hf_image as adapter

    monkeypatch.setattr(
        registry,
        "registry",
        lambda: [
            {
                "name": "image",
                "available": True,
                "runtime": "huggingface_image",
                "file_path": "model.safetensors",
                "version": "experimental",
            }
        ],
    )

    def fail(*args):
        raise ValueError("Invalid checkpoint")

    monkeypatch.setattr(adapter, "infer", fail)
    evidence = predict_media(tmp_path / "input.jpg", "image", "root")
    assert evidence.score is None and evidence.label == "unavailable"

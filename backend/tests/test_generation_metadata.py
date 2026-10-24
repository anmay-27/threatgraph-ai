from app.analyzers.image.generation import generation_markers


def test_explicit_generation_parameters_are_reported():
    assert generation_markers({"parameters": "a mountain\nSteps: 20, Sampler: Euler, Seed: 123"}, {})
    assert generation_markers({"prompt": '{"1":{"class_type":"KSampler"}}'}, {})


def test_ordinary_text_and_editing_are_not_generation_proof():
    assert generation_markers({"description": "AI art", "prompt": "not JSON"}, {"Software": "Adobe Photoshop"}) == []
    assert generation_markers({"parameters": "Steps: 20"}, {}) == []
    assert generation_markers({}, {}) == []

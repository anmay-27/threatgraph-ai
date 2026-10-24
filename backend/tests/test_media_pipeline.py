"""Architecture/preprocessing checks, not detector accuracy experiments."""

from pathlib import Path
import pytest
from PIL import Image


def test_media_networks_and_preprocessing():
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    from ml.common.model import Detector
    from ml.common.media import image_tensor, audio_chunks, face_frames

    torch.set_num_threads(2)
    tensor = image_tensor(Image.new("RGB", (320, 240), "green"))
    assert tensor.shape == (3, 224, 224)
    # Untrained networks are used only for a forward/backward shape smoke test.
    model = Detector("image", pretrained=False)
    logits, embedding = model(tensor.unsqueeze(0))
    assert logits.shape == (1,) and embedding.shape == (1, 512)
    logits.sum().backward()
    assert model.head[1].weight.grad is not None
    pytest.importorskip("librosa")
    chunks = audio_chunks(Path("datasets/demo/tone.wav"))
    assert chunks[0][0].shape[0:2] == (1, 64)
    assert chunks[0][2] == 2
    audio_model = Detector("audio", pretrained=False).eval()
    logits, embedding = audio_model(chunks[0][0].unsqueeze(0))
    assert logits.shape == (1,) and embedding.shape == (1, 128)
    assert face_frames(Path("datasets/demo/shapes.avi")) == []


def test_media_manifest_blocks_source_leakage(tmp_path):
    pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    from ml.common.data import read_manifest

    Image.new("RGB", (8, 8), "blue").save(tmp_path / "a.png")
    (tmp_path / "manifest.csv").write_text(
        "path,label,split,group,generator\na.png,0,train,identity,camera\na.png,1,test,identity,generator\n"
    )
    with pytest.raises(ValueError, match="leakage"):
        read_manifest(tmp_path)

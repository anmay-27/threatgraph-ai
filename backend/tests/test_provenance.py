from pathlib import Path
import pytest
from app.analyzers.provenance.inspect import inspect_provenance


def test_real_signed_and_tampered_provenance():
    pytest.importorskip("c2pa")
    signed = Path("storage/c2pa-official.jpg")
    tampered = Path("storage/c2pa-tampered.jpg")
    if not signed.exists() or not tampered.exists():
        pytest.skip("Optional official C2PA fixture was not downloaded")
    result = inspect_provenance(signed, "signed")
    assert result[0].metadata["present"] is True
    assert result[0].metadata["valid"] is True
    result = inspect_provenance(tampered, "tampered")
    assert result[0].metadata["valid"] is False

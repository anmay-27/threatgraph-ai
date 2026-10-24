import io
import time
import wave
import cv2
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app, requests
from app.models.database import Session, Analysis, ENTITIES
from sqlalchemy import select


def await_result(client, identifier):
    for _ in range(200):
        row = client.get("/api/v1/analyses/" + identifier).json()
        if row["state"] not in ("QUEUED", "PROCESSING"):
            return row
        time.sleep(0.05)
    raise AssertionError("Worker did not finish")


def test_image_workflow():
    buffer = io.BytesIO()
    Image.new("RGB", (100, 80), "green").save(buffer, format="PNG")
    with TestClient(app) as client:
        requests.clear()
        response = client.post(
            "/api/v1/analyze/file",
            files={"file": ("../../photo.png", buffer.getvalue(), "text/plain")},
        )
        assert response.status_code == 202, response.text
        result = await_result(client, response.json()["id"])
        assert result["input_type"] == "image"
        assert result["state"] == "PARTIAL"
        assert result["report"]["verdict"] == "INCONCLUSIVE"
        assert result["name"] == "photo.png"
        assert any(e["label"] == "image_metadata" for e in result["report"]["evidence"])
        assert (
            len(
                client.get("/api/v1/analyses/" + result["id"] + "/graph").json()[
                    "nodes"
                ]
            )
            > 1
        )
        with Session() as db:
            assert db.get(Analysis, result["id"]).report
            assert db.scalars(
                select(ENTITIES["evidence"]).where(
                    ENTITIES["evidence"].analysis_id == result["id"]
                )
            ).all()


def test_audio_and_generic():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(bytes(32000))
    with TestClient(app) as client:
        requests.clear()
        for name, data, kind in [
            ("test.wav", buffer.getvalue(), "audio"),
            ("notes.txt", b"local test document", "file"),
        ]:
            response = client.post("/api/v1/analyze/file", files={"file": (name, data)})
            result = await_result(client, response.json()["id"])
            assert result["input_type"] == kind
            assert result["state"] == "PARTIAL"


def test_video_upload(tmp_path):
    path = tmp_path / "sample.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 64))
    for _ in range(10):
        writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
    writer.release()
    with TestClient(app) as client:
        requests.clear()
        response = client.post(
            "/api/v1/analyze/file", files={"file": ("sample.avi", path.read_bytes())}
        )
        result = await_result(client, response.json()["id"])
        assert result["input_type"] == "video"
        assert result["state"] == "PARTIAL"
        assert any(e["label"] == "video_metadata" for e in result["report"]["evidence"])


def test_url_fetch_workflow(monkeypatch):
    from app.core.fetch import FetchResult

    async def fake_fetch(url, *args):
        return FetchResult(
            url,
            b'<html><body>Microsoft verify immediately<form action="https://collector.example/"><input type="password"></form></body></html>',
            "text/html",
            [],
            200,
        )

    monkeypatch.setattr("app.services.investigation.fetch", fake_fetch)
    with TestClient(app) as client:
        requests.clear()
        response = client.post(
            "/api/v1/analyze/url", json={"url": "https://login.example/"}
        )
        result = await_result(client, response.json()["id"])
        assert result["state"] == "PARTIAL"
        assert result["report"]["risk_score"] >= 70
        assert result["report"]["scenarios"]


def test_validation_and_preview():
    with TestClient(app) as client:
        requests.clear()
        assert (
            client.post(
                "/api/v1/analyze/url", json={"url": "http://127.0.0.1"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/analyze/file", files={"file": ("empty.txt", b"")}
            ).status_code
            == 422
        )
        assert client.get("/api/v1/analyses/missing").status_code == 404

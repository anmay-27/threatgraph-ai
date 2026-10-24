import io
import zipfile
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app, requests
from app.models.database import Analysis, Session
from app.analyzers.file.inspect import inspect_file
from app.workers.tasks import cleanup


def test_upload_size_and_rate_limits(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    with TestClient(app) as client:
        requests.clear()
        response = client.post(
            "/api/v1/analyze/file",
            files={"file": ("large.bin", bytes(1024 * 1024 + 1))},
        )
        assert response.status_code == 413
        requests.clear()
        for _ in range(12):
            assert (
                client.post(
                    "/api/v1/analyze/url", json={"url": "http://127.0.0.1/"}
                ).status_code
                == 422
            )
        assert (
            client.post(
                "/api/v1/analyze/url", json={"url": "http://127.0.0.1/"}
            ).status_code
            == 429
        )
        requests.clear()


def test_archive_is_only_inventoried(tmp_path):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("../escape.txt", "A" * 1024 * 1024)
    path = tmp_path / "archive.zip"
    path.write_bytes(data.getvalue())
    _, evidence = inspect_file(path, "archive.zip", "asset")
    labels = {e.label for e in evidence}
    assert {"archive_path_traversal", "archive_limits"} <= labels
    assert not (tmp_path.parent / "escape.txt").exists()


def test_retention_keeps_report_and_removes_only_original(monkeypatch):
    monkeypatch.setattr(settings, "retention_hours", 1)
    with TestClient(app):
        path = settings.storage_dir / "retention-test"
        path.write_bytes(b"private original")
        with Session() as db:
            row = Analysis(
                name="retention",
                input_type="file",
                state="PARTIAL",
                path=str(path.resolve()),
                created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                report={"evidence": []},
            )
            db.add(row)
            db.commit()
            identifier = row.id
        cleanup.run()
        with Session() as db:
            row = db.get(Analysis, identifier)
            assert row.path is None and row.report == {"evidence": []}
        assert not path.exists()

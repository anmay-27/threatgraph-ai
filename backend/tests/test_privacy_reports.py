from pathlib import Path
import fitz
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app, requests
from app.models.database import Analysis, Session
from app.models.intelligence import Entity
from app.core.config import settings
from app.services.intelligence import index_analysis
from app.services.reports import render_pdf


def test_image_pdf_explains_false_negative_and_next_steps():
    report = {
        "risk_level": "UNKNOWN", "confidence": 0.35, "uncertainty": "high",
        "evidence": [{"id": "model-1", "source": "image_detector", "label": "synthetic_probability",
                      "severity": "info", "score": 0.099, "model_version": "research-v3",
                      "metadata": {"verdict": "likely_real", "ood": "not_estimated",
                                   "stability_checks": [{"name": "Original image", "score": 0.099}]},
                      "explanation": "Research classifier output."}],
        "graph": {"nodes": [], "edges": []},
    }
    payload = render_pdf("Investigation report", "example-id", [
        {"id": "example-id", "name": "portrait.jpeg", "input_type": "image",
         "state": "COMPLETED", "report": report}])
    with fitz.open(stream=payload, filetype="pdf") as pdf:
        text = "\n".join(page.get_text() for page in pdf)
    assert "9.9%" in text
    assert "FALSE NEGATIVE" in text
    assert "How to verify and improve" in text
    assert "cannot locate altered pixels" in text


def test_reviewer_correction_appears_separately_in_new_pdf():
    with TestClient(app) as client:
        requests.clear()
        with Session() as db:
            row = Analysis(name="portrait.jpeg", input_type="image", state="COMPLETED",
                           report={"risk_level": "UNKNOWN", "graph": {"nodes": [], "edges": []},
                                   "evidence": [{"id": "model-1", "source": "image_detector",
                                                 "label": "synthetic_probability", "score": .099,
                                                 "severity": "info", "explanation": "Model score"}]})
            db.add(row)
            db.commit()
            identifier = row.id
        response = client.post(f"/api/v1/analyses/{identifier}/feedback", json={
            "evidence_id": "model-1", "verdict": "incorrect",
            "note": "User reports known AI-generated origin. Basis: created with my generator"})
        assert response.status_code == 201
        listed = client.get(f"/api/v1/analyses/{identifier}/feedback")
        assert listed.status_code == 200
        assert listed.json()[0]["used_for_training"] is False
        payload = client.get(f"/api/v1/analyses/{identifier}/report.pdf")
        with fitz.open(stream=payload.content, filetype="pdf") as pdf:
            text = " ".join(" ".join(page.get_text() for page in pdf).split())
        assert "9.9%" in text
        assert "Reviewer statement" in text
        assert "created with my generator" in text
        client.delete(f"/api/v1/analyses/{identifier}")


def test_export_and_delete_clean_storage_and_index():
    with TestClient(app) as client:
        requests.clear()
        path = settings.storage_dir / "delete-test"
        path.write_text("test")
        with Session() as db:
            row = Analysis(
                name="https://delete-only.example/",
                input_type="file",
                path=str(path),
                state="COMPLETED",
                report={"risk_level": "UNKNOWN", "graph": {"nodes": [], "edges": []}},
            )
            db.add(row)
            db.flush()
            index_analysis(db, row)
            db.commit()
            identifier = row.id
        response = client.get(f"/api/v1/analyses/{identifier}/report.pdf")
        assert response.status_code == 200
        with fitz.open(stream=response.content, filetype="pdf") as pdf:
            assert "Executive Summary" in "".join(p.get_text() for p in pdf)
        assert (
            client.delete(f"/api/v1/analyses/{identifier}/original").status_code == 200
        )
        assert not path.exists()
        assert client.get(f"/api/v1/analyses/{identifier}").status_code == 200
        assert client.delete(f"/api/v1/analyses/{identifier}").status_code == 200
        with Session() as db:
            assert not db.scalar(
                select(Entity).where(Entity.normalized_value == "delete-only.example")
            )


def test_deletion_refuses_active_jobs_and_outside_paths(tmp_path):
    with TestClient(app) as client:
        with Session() as db:
            row = Analysis(name="active", state="PROCESSING")
            db.add(row)
            db.commit()
            identifier = row.id
        assert client.delete("/api/v1/analyses/" + identifier).status_code == 409
        outside = tmp_path / "outside.txt"
        outside.write_text("keep")
        with Session() as db:
            row = db.get(Analysis, identifier)
            row.state = "FAILED"
            row.path = str(outside)
            db.commit()
        assert client.delete("/api/v1/analyses/" + identifier).status_code == 409
        assert outside.read_text() == "keep"

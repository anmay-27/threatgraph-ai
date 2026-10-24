from fastapi.testclient import TestClient
from app.main import app, requests
from app.models.database import Analysis, Session


def test_case_lifecycle_preserves_analyses():
    with TestClient(app) as client:
        requests.clear()
        with Session() as db:
            a = Analysis(
                name="case test",
                input_type="file",
                state="COMPLETED",
                report={
                    "graph": {
                        "nodes": [{"id": "n", "type": "file", "label": "test"}],
                        "edges": [],
                    }
                },
            )
            db.add(a)
            db.commit()
            aid = a.id
        created = client.post(
            "/api/v1/cases", json={"title": "Job offer", "tags": ["job", "job", " "]}
        )
        assert created.status_code == 201
        cid = created.json()["id"]
        assert created.json()["tags"] == ["job"]
        path = "/api/v1/cases/" + cid
        assert client.post(path + "/analyses/" + aid).status_code == 200
        assert client.post(path + "/analyses/" + aid).status_code == 200
        assert (
            client.post(
                path + "/notes", json={"content": "Verify recruiter independently."}
            ).status_code
            == 201
        )
        assert (
            client.put(
                path,
                json={
                    "title": "Updated job offer",
                    "status": "REVIEW_REQUIRED",
                    "tags": ["job"],
                },
            ).status_code
            == 200
        )
        detail = client.get(path).json()
        assert len(detail["analyses"]) == 1
        assert detail["graph"]["nodes"][0]["id"] == aid + ":n"
        assert len(detail["timeline"]) == 4
        assert client.delete(path + "/analyses/" + aid).status_code == 200
        assert client.get(path).json()["analyses"] == []
        assert client.delete(path).json()["analyses_preserved"]
        assert client.get(path).status_code == 404
        assert client.get("/api/v1/analyses/" + aid).status_code == 200


def test_case_validation_and_missing_records():
    with TestClient(app) as client:
        requests.clear()
        assert client.post("/api/v1/cases", json={"title": "   "}).status_code == 422
        assert (
            client.post(
                "/api/v1/cases", json={"title": "x", "status": "FAKE"}
            ).status_code
            == 422
        )
        cid = client.post("/api/v1/cases", json={"title": "Validation"}).json()["id"]
        assert (
            client.post("/api/v1/cases/" + cid + "/analyses/missing").status_code == 404
        )
        assert (
            client.post(
                "/api/v1/cases/" + cid + "/notes", json={"content": "  "}
            ).status_code
            == 422
        )
        assert client.get("/api/v1/cases/missing").status_code == 404
        assert client.delete("/api/v1/cases/missing").status_code == 404

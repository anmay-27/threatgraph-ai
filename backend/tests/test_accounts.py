from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app, requests
from app.core.config import settings
from app.models.database import Analysis, Session
from app.services.auth import Account, AnalysisOwner
from app.services.intelligence import index_analysis


def test_accounts_isolate_all_report_surfaces(monkeypatch):
    monkeypatch.setattr(settings, "auth_required", True)
    with TestClient(app) as client:
        requests.clear()
        assert client.get("/api/v1/history").status_code == 401
        users = []
        for email in ("one@isolation.example", "two@isolation.example"):
            credentials = {"email": email, "password": "long-password-for-test"}
            assert (
                client.post("/api/v1/auth/register", json=credentials).status_code
                == 201
            )
            with Session() as db:
                account = db.scalar(select(Account).where(Account.email == email))
                account.role = "ANALYST"
                db.commit()
                users.append(account.id)
        with Session() as db:
            a = Analysis(
                name="https://private-correlation.example/",
                input_type="url",
                state="COMPLETED",
                report={"graph": {"nodes": [], "edges": []}},
            )
            db.add(a)
            db.flush()
            db.add(AnalysisOwner(analysis_id=a.id, owner_id=users[0]))
            index_analysis(db, a)
            db.commit()
            aid = a.id
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "one@isolation.example",
                    "password": "long-password-for-test",
                },
            ).status_code
            == 200
        )
        cid = client.post("/api/v1/cases", json={"title": "Private case"}).json()["id"]
        assert client.post(f"/api/v1/cases/{cid}/analyses/{aid}").status_code == 200
        entity = client.get("/api/v1/entities/search?q=private-correlation").json()[0][
            "id"
        ]
        assert client.post("/api/v1/auth/logout").status_code == 200
        requests.clear()
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "two@isolation.example",
                    "password": "long-password-for-test",
                },
            ).status_code
            == 200
        )
        for suffix in (
            "",
            "/status",
            "/graph",
            "/evidence",
            "/media",
            "/entities",
            "/report.pdf",
        ):
            assert client.get("/api/v1/analyses/" + aid + suffix).status_code == 404, (
                suffix
            )
        assert client.get("/api/v1/entities/" + entity).status_code == 404
        assert client.get("/api/v1/entities/search?q=private-correlation").json() == []
        assert (
            client.get("/api/v1/intelligence/graph?q=private-correlation").json()[
                "nodes"
            ]
            == []
        )
        assert client.get("/api/v1/cases/" + cid).status_code == 404
        assert client.get("/api/v1/cases/" + cid + "/report.pdf").status_code == 404
        assert client.get("/api/v1/history").json() == []
        assert client.get("/api/v1/dashboard").json()["total"] == 0
        issued = client.post("/api/v1/auth/token").json()["token"]
        assert (
            client.get(
                "/api/v1/history", headers={"Authorization": "Bearer " + issued}
            ).status_code
            == 200
        )
        assert client.get("/api/v1/admin/health").status_code == 403
        assert client.delete("/api/v1/analyses/" + aid).status_code == 404
        assert (
            client.post(
                "/api/v1/analyze/message",
                json={"text": "test"},
                headers={"Origin": "https://untrusted.example"},
            ).status_code
            == 403
        )

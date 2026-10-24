"""Exercise real HTTP, queue, database, decoders and persistence in the local stack."""

import argparse
import json
import time
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    results = []
    with httpx.Client(base_url=args.base_url, timeout=40, trust_env=False) as client:
        health = client.get("/api/v1/health").raise_for_status().json()
        assert health["queue_mode"] == "celery", (
            "This smoke test requires the durable Docker queue"
        )
        for filename in [
            "illustration.png",
            "tone.wav",
            "shapes.avi",
            "simulated-phishing.html",
        ]:
            path = Path("datasets/demo") / filename
            response = client.post(
                "/api/v1/analyze/file", files={"file": (filename, path.read_bytes())}
            )
            response.raise_for_status()
            identifier = response.json()["id"]
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                row = (
                    client.get("/api/v1/analyses/" + identifier)
                    .raise_for_status()
                    .json()
                )
                if row["state"] not in ("QUEUED", "PROCESSING"):
                    break
                time.sleep(0.5)
            assert row["state"] in ("COMPLETED", "PARTIAL"), row
            assert row["report"]["graph"]["nodes"]
            if filename.endswith(".html"):
                assert row["report"]["scenarios"], (
                    "Static phishing indicators should produce a scenario"
                )
            summary = {
                "input": filename,
                "id": identifier,
                "state": row["state"],
                "type": row["input_type"],
                "risk_score": row["report"]["risk_score"],
                "verdict": row["report"]["verdict"],
                "evidence_count": len(row["report"]["evidence"]),
                "graph_nodes": len(row["report"]["graph"]["nodes"]),
                "unavailable": [
                    e["source"]
                    for e in row["report"]["evidence"]
                    if e["label"] == "unavailable"
                ],
            }
            results.append(summary)
            print(summary, flush=True)
        history = client.get("/api/v1/history").raise_for_status().json()
        assert all(
            any(row["id"] == result["id"] for row in history) for result in results
        )
        assert (
            client.post(
                "/api/v1/analyze/url", json={"url": "http://127.0.0.1/"}
            ).status_code
            == 422
        )
        records = client.get("/api/v1/models").raise_for_status().json()
        assert any(r["name"] == "url" and r["available"] for r in records)
    output = Path("research/results/docker_smoke.json")
    output.write_text(
        json.dumps(
            {"health": health, "results": results, "persistence_verified": True},
            indent=2,
        )
    )
    print("Docker queue/database/media workflow smoke checks passed.")


if __name__ == "__main__":
    main()

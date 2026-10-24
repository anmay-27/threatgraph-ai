"""Create a fresh local report from a retained image; preserve the old report."""
import json
import sys
import time
from pathlib import Path
import requests

base = "http://127.0.0.1:8000/api/v1"
original = requests.get(f"{base}/analyses/{sys.argv[1]}", timeout=20)
original.raise_for_status()
row = original.json()
assert row["input_type"] == "image"
media = requests.get(f"{base}/analyses/{row['id']}/media", timeout=30)
media.raise_for_status()
response = requests.post(f"{base}/analyze/file", files={"file": (row["name"], media.content, row["mime"])}, timeout=30)
response.raise_for_status()
identifier = response.json()["id"]
print("New investigation:", identifier, flush=True)
for _ in range(90):
    response = requests.get(f"{base}/analyses/{identifier}", timeout=20)
    response.raise_for_status()
    result = response.json()
    if result["state"] in ("COMPLETED", "PARTIAL", "FAILED"):
        output = {"id": identifier, "state": result["state"], "model_results": (result.get("report") or {}).get("model_results"), "error": result.get("error")}
        Path("research/results/image_inference_smoke.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output, indent=2))
        assert any(e["source"] == "image_detector" and e["score"] is not None for e in output["model_results"] or []), "Image inference did not complete"
        break
    time.sleep(2)
else:
    raise TimeoutError("Investigation did not finish in 180 seconds")

"""Install a pinned, public Apache-2.0 image classifier for local inference."""

import hashlib
import argparse
import json
from pathlib import Path
import requests

REPO = "Ateeqq/ai-vs-human-image-detector"
REVISION = "60e82406916921b823616bee33397baab38af3f0"
root = Path(__file__).resolve().parents[1] / "models" / "image"
root.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("--replace", action="store_true", help="Explicitly replace a project-trained image registry with the experimental external model")
args = parser.parse_args()
existing = root / "registry.json"
if existing.exists() and json.loads(existing.read_text()).get("runtime") == "torch_media" and not args.replace:
    raise SystemExit("A project-trained image detector is installed. Keep it, or explicitly pass --replace to select the external model.")
for name in (
    "config.json",
    "preprocessor_config.json",
    "README.md",
    "model.safetensors",
):
    destination = root / name
    if destination.exists():
        continue
    print(f"Downloading {name}", flush=True)
    with requests.get(
        f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}",
        stream=True,
        timeout=(20, 120),
    ) as response:
        response.raise_for_status()
        temporary = destination.with_suffix(destination.suffix + ".part")
        with temporary.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                output.write(chunk)
        temporary.replace(destination)
record = {
    "version": "siglip-" + REVISION[:12],
    "architecture": "SiglipForImageClassification",
    "runtime": "huggingface_image",
    "threshold": 0.8,
    "file_path": "model.safetensors",
    "deployment_status": "experimental",
    "source": "https://huggingface.co/" + REPO,
    "revision": REVISION,
    "license": "Apache-2.0",
    "sha256": hashlib.file_digest(
        (root / "model.safetensors").open("rb"), "sha256"
    ).hexdigest(),
    "limitation": "Publisher reports overfitting. Not independently validated here. Scores are uncalibrated; certificates, screenshots, composites and unseen generators may be misclassified.",
}
(root / "registry.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print("Installed experimental local image classifier", flush=True)

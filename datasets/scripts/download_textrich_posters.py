"""Download the two CommercialPosters folders for external research evaluation.

The dataset is never used for training or calibration. Source labels and image
rights are described by the TextRich dataset card on Hugging Face.
"""

import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import requests


REPO = "Shuyiww/TextRich"
ROOT = Path("datasets/external/textrich-commercial-posters")


def main():
    session = requests.Session()
    info = session.get(f"https://huggingface.co/api/datasets/{REPO}", timeout=30)
    info.raise_for_status()
    revision = info.json()["sha"]
    records = []
    for label, folder in ((0, "0_real"), (1, "1_fake")):
        prefix = f"Data/CommercialPosters/{folder}"
        listing = session.get(f"https://huggingface.co/api/datasets/{REPO}/tree/{revision}/{prefix}", params={"expand": "true"}, timeout=30)
        listing.raise_for_status()
        files = sorted((item for item in listing.json() if item.get("type") == "file"), key=lambda item: item["path"])
        if len(files) != 50:
            raise RuntimeError(f"Expected 50 images in {folder}, found {len(files)}")
        for index, item in enumerate(files):
            if item.get("size", 0) > 5_000_000:
                raise RuntimeError("Unexpected oversized poster")
            suffix = Path(item["path"]).suffix.lower()
            target = ROOT / f"{folder}-{index:03d}{suffix}"
            url = f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/{quote(item['path'], safe='/')}"
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with session.get(url, stream=True, timeout=60) as response:
                    response.raise_for_status()
                    with target.open("wb") as output:
                        for chunk in response.iter_content(65536):
                            output.write(chunk)
                            if output.tell() > 5_000_000:
                                raise RuntimeError("Download exceeded poster limit")
            if target.stat().st_size != item["size"]:
                raise RuntimeError(f"Size mismatch: {target}")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            records.append({"path": target.name, "label": label, "source_path": item["path"], "sha256": digest})
    with (ROOT / "manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (ROOT / "source.json").write_text(json.dumps({
        "repository": REPO, "revision": revision,
        "dataset_card": f"https://huggingface.co/datasets/{REPO}",
        "purpose": "Held-out commercial-poster evaluation only; no train/calibration overlap",
        "labels": "0 = real template poster (Crello subset); 1 = GPT-Image-2 generated poster, per dataset authors",
        "count": len(records),
        "limitation": "50/50 fixed poster sample; one synthetic generator and real-source licensing/selection limit generalization",
    }, indent=2), encoding="utf-8")
    print(json.dumps({"revision": revision, "count": len(records), "bytes": sum((ROOT / r["path"]).stat().st_size for r in records)}))


if __name__ == "__main__":
    main()

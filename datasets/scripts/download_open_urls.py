"""Fetch only the openly licensed UCI PhiUSIIL archive, with bounded download."""

import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip"


def main():
    root = Path("datasets/raw/phiusiil")
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "dataset.zip"
    with urllib.request.urlopen(URL, timeout=60) as response, archive.open("wb") as out:
        size = 0
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > 30 * 1024 * 1024:
                raise ValueError("Unexpectedly large archive")
            out.write(chunk)
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            if entry.filename.endswith(".csv") and entry.file_size < 100 * 1024 * 1024:
                (root / "urls.csv").write_bytes(z.read(entry))
    (root / "source.json").write_text(
        json.dumps(
            {
                "url": URL,
                "license": "CC BY 4.0",
                "citation": "Prasad, A. & Chandra, S. (2024). PhiUSIIL Phishing URL (Website). UCI Machine Learning Repository. doi:10.1016/j.cose.2023.103545",
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )
    print("Downloaded licensed URL records. No listed URL was visited.")


if __name__ == "__main__":
    main()

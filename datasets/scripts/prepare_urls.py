"""Convert approved local feeds into a URL/label/source CSV; never visit feed URLs."""

import argparse
import csv
import io
import json
from pathlib import Path


def prepare(source: Path, kind: str, output: Path):
    rows = []
    text = source.read_text(encoding="utf-8-sig")
    if kind == "phishtank":
        for row in json.loads(text):
            if row.get("verified") in ("yes", True) and row.get("online") in (
                "yes",
                True,
            ):
                rows.append((row["url"], 1, kind))
    elif kind == "urlhaus":
        content = "\n".join(
            line for line in text.splitlines() if not line.startswith("#")
        )
        for row in csv.reader(io.StringIO(content)):
            if len(row) >= 3 and row[2].startswith(("http://", "https://")):
                rows.append((row[2], 1, kind))
    elif kind == "phiusiil":
        for row in csv.DictReader(io.StringIO(text)):
            rows.append((row["URL"], 1 - int(row["label"]), kind))
    elif kind == "toplist":
        for row in csv.reader(io.StringIO(text)):
            host = row[-1].strip()
            if "." in host:
                rows.append(("https://" + host + "/", 0, kind))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["url", "label", "source"])
        writer.writerows(rows)
    print(f"Prepared {len(rows)} rows: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--kind", choices=["phishtank", "urlhaus", "phiusiil", "toplist"], required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.kind, args.output)

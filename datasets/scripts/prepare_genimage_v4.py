"""Repartition the existing duplicate-filtered v3 source without test leakage.

This provides 1,000 training images. It does not add poster examples or claim
that the source distribution represents modern user uploads.
"""

import csv
import json
import os
import random
from collections import Counter
from pathlib import Path


def main():
    source = Path("datasets/prepared/tiny-genimage-v3")
    target = Path("datasets/prepared/tiny-genimage-v4")
    if target.exists():
        raise RuntimeError("Target exists; prepared experiment inputs are immutable")
    rows = list(csv.DictReader((source / "manifest.csv").open(encoding="utf-8-sig")))
    development = [r for r in rows if r["split"] in {"train", "validation", "calibration"}]
    untouched = [r for r in rows if r["split"] in {"test", "ood"}]
    assert len(development) == 1200 and len(untouched) == 800
    rng = random.Random(20261019)
    chosen = []
    for label in ("0", "1"):
        pool = [r for r in development if r["label"] == label]
        assert len(pool) == 600
        rng.shuffle(pool)
        for split, start, end in (("train", 0, 500), ("validation", 500, 550), ("calibration", 550, 600)):
            chosen.extend({**r, "split": split} for r in pool[start:end])
    chosen.extend(untouched)
    rng.shuffle(chosen)
    target.mkdir(parents=True)
    images = target / "images"
    images.mkdir()
    for r in chosen:
        original = source / r["path"]
        destination = target / r["path"]
        os.link(original, destination)
    with (target / "manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(chosen)
    audit = {
        "source": str(source),
        "seed": 20261019,
        "counts": dict(Counter(r["split"] for r in chosen)),
        "labels": {s: dict(Counter(r["label"] for r in chosen if r["split"] == s)) for s in ("train", "validation", "calibration", "test", "ood")},
        "policy": "Only v3 development rows repartitioned; v3 test and held-out Midjourney OOD rows unchanged. v3 global identity/pHash duplicate checks inherited.",
        "limitations": ["No poster-specific examples", "Fixed GenImage derivative, not a representative field sample", "Upstream pretrained encoder overlap is unknown"],
    }
    (target / "preparation.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()

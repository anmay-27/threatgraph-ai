"""Prepare face crops from approved source videos; preserve source group and split."""

import argparse
import csv
from pathlib import Path
from ml.common.media import face_frames

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    output = []
    for index, row in enumerate(csv.DictReader(a.manifest.open())):
        path = (a.manifest.parent / row["path"]).resolve()
        if not path.is_relative_to(a.manifest.parent.resolve()):
            raise ValueError("Unsafe dataset path")
        for frame, (image, time) in enumerate(face_frames(path)):
            name = f"{index}_{frame}.jpg"
            image.save(a.output_dir / name, quality=95)
            output.append(
                {**row, "path": name, "timestamp": time, "source_video": row["path"]}
            )
    if not output:
        raise ValueError("No faces detected")
    with (a.output_dir / "manifest.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)

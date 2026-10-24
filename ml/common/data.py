import csv
import hashlib
from pathlib import Path
from PIL import Image
import torch
from torch.utils.data import Dataset
from ml.common.media import image_tensor, audio_chunks


def read_manifest(directory: Path):
    rows = list(csv.DictReader((directory / "manifest.csv").open(encoding="utf-8-sig")))
    required = {"path", "label", "split", "group", "generator"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Manifest requires path,label,split,group,generator")
    groups, hashes = {}, {}
    root = directory.resolve()
    for row in rows:
        if row["split"] not in ("train", "validation", "calibration", "test", "ood") or row[
            "label"
        ] not in ("0", "1"):
            raise ValueError("Invalid manifest label/split")
        path = (directory / row["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Dataset path missing or outside dataset directory")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for key, store in ((row["group"], groups), (digest, hashes)):
            if key in store and store[key] != row["split"]:
                raise ValueError("Source identity/content leakage across splits")
            store[key] = row["split"]
    for split in ("train", "validation", "test"):
        if {r["label"] for r in rows if r["split"] == split} != {"0", "1"}:
            raise ValueError(f"{split} must contain both classes")
    return rows


class MediaDataset(Dataset):
    def __init__(self, root, rows, modality, augment=False):
        self.root, self.rows, self.modality, self.augment = (
            root,
            rows,
            modality,
            augment,
        )

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        path = self.root / row["path"]
        if self.modality == "audio":
            # Manifest audio utterances should be <=4s for consistent training.
            chunks = audio_chunks(path, self.augment)
            if self.augment:
                tensor = chunks[int(torch.randint(len(chunks), (1,)).item())][0]
            else:
                tensor = chunks[0][0]
        else:
            with Image.open(path) as image:
                tensor = image_tensor(image, self.augment)
        return tensor, torch.tensor(int(row["label"]), dtype=torch.float32)

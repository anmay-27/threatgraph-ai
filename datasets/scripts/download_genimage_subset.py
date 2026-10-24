"""Download pinned public Tiny-GenImage shards, not the full dataset."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import requests

REPO = "TheKernel01/Tiny-GenImage"
REVISION = "89c4fe9efd0ebc7ce5c7641ef57d578ccd639c69"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("datasets/raw/tiny-genimage"))
    parser.add_argument("--train-shards", type=int, nargs='*', default=[0])
    parser.add_argument("--validation-shards", type=int, nargs='+', default=[0])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    root = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}"
    response = requests.get(f"https://huggingface.co/api/datasets/{REPO}/tree/{REVISION}/data?limit=100", timeout=60)
    response.raise_for_status()
    files = response.json()
    # Fixed, disclosed shard selection. No benchmark scores influence sampling.
    selected = [next(f for f in files if f["path"].startswith(f"data/{split}-{index:05d}-")) for split, indices in [('train', args.train_shards), ('validation', args.validation_shards)] for index in sorted(set(indices))]
    card = requests.get(root + "/README.md", timeout=60)
    card.raise_for_status()
    (args.output_dir / "SOURCE.md").write_text(card.text, encoding="utf-8")
    def download(item):
        target = args.output_dir / Path(item["path"]).name
        expected = item["lfs"]["oid"]
        if target.exists() and hashlib.file_digest(target.open("rb"), "sha256").hexdigest() == expected:
            return
        temporary = target.with_suffix(".part")
        for attempt in range(3):
            try:
                print("Downloading", item["path"], "bytes", item["size"], flush=True)
                offset = temporary.stat().st_size if temporary.exists() else 0
                if offset >= item["size"]:
                    with temporary.open("rb") as partial:
                        complete_hash = hashlib.file_digest(partial, "sha256").hexdigest()
                    if offset == item["size"] and complete_hash == expected:
                        temporary.replace(target)
                        print("Verified", target.name, flush=True)
                        return
                    temporary.write_bytes(b"")
                    offset = 0
                headers = {"Range": f"bytes={offset}-"} if offset else {}
                with requests.get(root + "/" + item["path"], headers=headers, stream=True, timeout=(30, 120)) as response:
                    response.raise_for_status()
                    if response.status_code == 206 and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                        raise ValueError("Unexpected partial download range")
                    with temporary.open("ab" if offset and response.status_code == 206 else "wb") as output:
                        for chunk in response.iter_content(1024 * 1024):
                            output.write(chunk)
                actual = hashlib.file_digest(temporary.open("rb"), "sha256").hexdigest()
                if actual != expected:
                    temporary.write_bytes(b"")
                    raise ValueError("Downloaded shard checksum mismatch")
                temporary.replace(target)
                print("Verified", target.name, flush=True)
                return
            except (requests.RequestException, ValueError):
                if attempt == 2:
                    raise
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, selected))
    (args.output_dir / "download_manifest.json").write_text(json.dumps({"repo": REPO, "revision": REVISION, "license": "CC-BY-NC-SA-4.0 (mirror declaration); underlying image rights remain with owners", "files": selected}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

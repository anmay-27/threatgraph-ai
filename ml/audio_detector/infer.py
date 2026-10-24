import argparse
import json
from pathlib import Path
from ml.common.inference import infer

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--input", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(infer(a.input, a.checkpoint, "audio"), indent=2))

"""Portable local development launcher (SQLite and bounded thread executor)."""

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path[:0] = [str(root / "backend"), str(root)]
os.environ.setdefault("TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/threatgraph.db")
os.environ.setdefault("CLAMAV_HOST", "127.0.0.1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000"))
    )

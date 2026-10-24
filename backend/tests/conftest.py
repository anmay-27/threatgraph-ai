import os
from pathlib import Path
import tempfile
import pytest

ROOT = tempfile.TemporaryDirectory(
    prefix="threatgraph-tests-", ignore_cleanup_errors=True
)
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(ROOT.name) / "test.db")
os.environ["STORAGE_DIR"] = str(Path(ROOT.name) / "uploads")
os.environ["MODEL_DIR"] = str(Path(ROOT.name) / "models")
os.environ["TASK_ALWAYS_EAGER"] = "true"


@pytest.fixture(scope="session", autouse=True)
def close_database():
    yield
    from app.models.database import engine

    engine.dispose()

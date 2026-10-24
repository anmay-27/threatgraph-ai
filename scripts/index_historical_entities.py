"""Idempotently index historical reports without rerunning detectors or fetching URLs."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / "backend"), str(root)]
from sqlalchemy import select
from app.models.database import Base, engine, Session, Analysis
from app.services.intelligence import index_analysis

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    count = 0
    with Session() as db:
        for row in db.scalars(
            select(Analysis).where(Analysis.report.is_not(None))
        ).yield_per(50):
            index_analysis(db, row)
            count += 1
        db.commit()
    print(f"Indexed {count} historical investigations. Reports unchanged.")

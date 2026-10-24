from app.services.intelligence import extract_text, index_analysis
from app.models.database import Base, Session, Analysis, engine
from app.models.intelligence import Entity, AnalysisEntity
from sqlalchemy import select, func


def test_normalization_preserves_path_and_query():
    rows = extract_text(
        "https://EXAMPLE.com:443/Path?Token=A#frag mail@EXAMPLE.com +91 98765 43210 upi://pay?pa=shop@upi&am=10"
    )
    assert ("URL", "https://example.com/Path?Token=A") in rows
    assert ("EMAIL", "mail@example.com") in rows
    assert ("PHONE_NUMBER", "+919876543210") in rows
    assert ("UPI_ID", "shop@upi") in rows
    assert not extract_text("https://user:secret@example.com/")


def test_repeated_entities_and_reindex_are_idempotent():
    Base.metadata.create_all(engine)
    with Session() as db:
        rows = [
            Analysis(
                name="https://correlation.example/path",
                input_type="url",
                state="COMPLETED",
                report={},
            )
            for _ in range(2)
        ]
        db.add_all(rows)
        db.flush()
        for row in rows:
            index_analysis(db, row)
        db.commit()
        index_analysis(db, rows[0])
        db.commit()
        entity = db.scalar(
            select(Entity).where(
                Entity.type == "DOMAIN",
                Entity.normalized_value == "correlation.example",
            )
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AnalysisEntity)
                .where(AnalysisEntity.entity_id == entity.id)
            )
            == 2
        )

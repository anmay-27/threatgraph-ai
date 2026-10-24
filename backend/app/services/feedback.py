from datetime import datetime
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base, Session, Analysis
from app.models.cases import now
from app.services.auth import accessible, principal, scope


class Feedback(Base):
    __tablename__ = "finding_feedback"
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[str]
    owner_id: Mapped[str]
    verdict: Mapped[str]
    note: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FeedbackInput(BaseModel):
    evidence_id: str = Field(max_length=100)
    verdict: Literal["accurate", "incorrect", "unsure"]
    note: str = Field(default="", max_length=2000)


router = APIRouter(prefix="/api/v1/analyses", tags=["feedback"])


@router.get("/{identifier}/feedback")
def list_feedback(identifier: str):
    with Session() as db:
        row = db.get(Analysis, identifier)
        if not row or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        records = db.scalars(
            select(Feedback).where(Feedback.analysis_id == identifier)
            .order_by(Feedback.created_at.desc()).limit(50)
        ).all()
        return [{"id": r.id, "evidence_id": r.evidence_id, "verdict": r.verdict,
                 "note": r.note, "created_at": r.created_at.isoformat(),
                 "used_for_training": False} for r in records]


@router.post("/{identifier}/feedback", status_code=201)
def feedback(identifier: str, body: FeedbackInput):
    with Session() as db:
        row = db.get(Analysis, identifier)
        if not row or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        if not any(
            e["id"] == body.evidence_id for e in (row.report or {}).get("evidence", [])
        ):
            raise HTTPException(422, "Finding is not part of this investigation")
        record = Feedback(
            analysis_id=identifier, owner_id=principal.get()["id"], **body.model_dump()
        )
        db.add(record)
        db.commit()
        return {"id": record.id, "saved": True, "used_for_training": False}


@router.get("/{identifier}/duplicates")
def duplicates(identifier: str):
    from app.services.intelligence import extract_text

    with Session() as db:
        row = db.get(Analysis, identifier)
        if not row or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        query = scope(
            select(Analysis)
            .where(Analysis.id != identifier)
            .order_by(Analysis.created_at.desc())
            .limit(500)
        )
        current_url = extract_text(row.name) if row.input_type == "url" else []

        def phash(a):
            return next(
                (
                    e.get("metadata", {}).get("perceptual_hash")
                    for e in (a.report or {}).get("evidence", [])
                    if e.get("label") == "image_metadata"
                ),
                None,
            )

        original = phash(row)
        matches = []
        for candidate in db.scalars(query):
            relation = None
            distance = None
            if row.sha256 and row.sha256 == candidate.sha256:
                relation = "identical_bytes"
            elif (
                current_url
                and candidate.input_type == "url"
                and extract_text(candidate.name) == current_url
            ):
                relation = "same_normalized_url"
            elif original and phash(candidate):
                try:
                    distance = (
                        int(original, 16) ^ int(phash(candidate), 16)
                    ).bit_count()
                except ValueError:
                    continue
                if distance <= 4:
                    relation = "visually_similar"
            if relation:
                matches.append(
                    {
                        "id": candidate.id,
                        "name": candidate.name,
                        "relation": relation,
                        "perceptual_hash_distance": distance,
                        "created_at": candidate.created_at,
                    }
                )
        return {
            "matches": matches,
            "searched_limit": 500,
            "limitation": "Visual similarity is not identity. Prior reports may use older models. Run a new analysis when current evidence is needed.",
        }

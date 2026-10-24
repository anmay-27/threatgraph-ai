from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import DateTime, ForeignKey, update
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base, Analysis, Session
from app.models.cases import now
from app.services.auth import accessible


class JobControl(Base):
    __tablename__ = "job_controls"
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True
    )
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    attempts: Mapped[int] = mapped_column(default=1)
    heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InvestigationCancelled(Exception):
    pass


def checkpoint(db, identifier):
    control = db.get(JobControl, identifier)
    if not control:
        control = JobControl(analysis_id=identifier)
        db.add(control)
    elif control.cancel_requested:
        raise InvestigationCancelled("Cancellation requested")
    control.heartbeat = now()


router = APIRouter(prefix="/api/v1/analyses", tags=["jobs"])


@router.post("/{identifier}/cancel")
def cancel(identifier: str):
    with Session() as db:
        row = db.get(Analysis, identifier)
        if not row or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        if row.state not in ("QUEUED", "PROCESSING"):
            raise HTTPException(409, "Job is not active")
        control = db.get(JobControl, identifier)
        if not control:
            control = JobControl(analysis_id=identifier)
            db.add(control)
        control.cancel_requested = True
        db.commit()
        return {
            "cancel_requested": True,
            "message": "Stops at the next safe pipeline boundary; an active model call may need to finish.",
        }


@router.post("/{identifier}/retry")
def retry(identifier: str):
    from pathlib import Path
    from app.main import queue

    with Session() as db:
        row = db.get(Analysis, identifier)
        if not row or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        if row.input_type != "url" and (not row.path or not Path(row.path).is_file()):
            raise HTTPException(410, "Original upload has expired; upload it again")
        result = db.execute(
            update(Analysis)
            .where(
                Analysis.id == identifier, Analysis.state.in_(["FAILED", "CANCELLED"])
            )
            .values(state="QUEUED", error=None, progress=[])
        )
        if result.rowcount != 1:
            raise HTTPException(409, "Only failed or cancelled jobs can be retried")
        control = db.get(JobControl, identifier)
        if control:
            if control.attempts >= 3:
                raise HTTPException(
                    409,
                    "Three attempts reached; create a new investigation after resolving the failure",
                )
            control.attempts += 1
            control.cancel_requested = False
            control.heartbeat = now()
        else:
            db.add(JobControl(analysis_id=identifier, attempts=2))
        db.commit()
        db.refresh(row)
    queue(row)
    return {"id": identifier, "state": "QUEUED"}

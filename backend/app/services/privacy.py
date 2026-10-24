from datetime import timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select, func
from app.models.database import Analysis, Session, ENTITIES
from app.models.cases import CaseAsset, CaseEvent
from app.models.intelligence import AnalysisEntity, Entity
from app.services.auth import accessible, AnalysisOwner
from app.core.config import settings
from app.services.feedback import Feedback
from app.services.jobs import JobControl

router = APIRouter(prefix="/api/v1/analyses", tags=["privacy"])


def checked(db, identifier):
    row = db.get(Analysis, identifier)
    if not row or not accessible(db, identifier):
        raise HTTPException(404, "Analysis not found")
    return row


def remove_original(row):
    if row.path:
        path = Path(row.path).resolve()
        if not path.is_relative_to(settings.storage_dir.resolve()):
            raise HTTPException(
                409, "Stored path is outside upload storage; manual review required"
            )
        path.unlink(missing_ok=True)
        row.path = None


@router.get("/{identifier}/privacy")
def privacy(identifier: str):
    with Session() as db:
        row = checked(db, identifier)
        return {
            "original_present": bool(row.path and Path(row.path).is_file()),
            "stored_until": row.created_at + timedelta(hours=settings.retention_hours),
            "retention_hours": settings.retention_hours,
            "policy": "Original uploads expire; reports remain until explicitly deleted.",
        }


@router.delete("/{identifier}/original")
def delete_original(identifier: str):
    with Session() as db:
        row = checked(db, identifier)
        if row.state in ("QUEUED", "PROCESSING"):
            raise HTTPException(
                409, "Wait for the active analysis before deleting its source"
            )
        remove_original(row)
        db.commit()
    return {"deleted": True, "report_preserved": True}


@router.delete("/{identifier}")
def delete_analysis(identifier: str):
    with Session() as db:
        row = checked(db, identifier)
        if row.state in ("QUEUED", "PROCESSING"):
            raise HTTPException(409, "Wait for the active analysis before deletion")
        entity_ids = list(
            db.scalars(
                select(AnalysisEntity.entity_id).where(
                    AnalysisEntity.analysis_id == identifier
                )
            )
        )
        remove_original(row)
        for table in (
            *ENTITIES.values(),
            AnalysisEntity,
            AnalysisOwner,
            CaseAsset,
            Feedback,
            JobControl,
        ):
            db.execute(delete(table).where(table.analysis_id == identifier))
        # Remove copied names and identifiers from case events as well.
        db.execute(delete(CaseEvent).where(CaseEvent.analysis_id == identifier))
        db.delete(row)
        db.flush()
        for entity_id in entity_ids:
            entity = db.get(Entity, entity_id)
            dates = db.execute(
                select(func.min(Analysis.created_at), func.max(Analysis.created_at))
                .join(AnalysisEntity)
                .where(AnalysisEntity.entity_id == entity_id)
            ).one()
            if dates[0] is None:
                db.delete(entity)
            else:
                entity.first_seen, entity.last_seen = dates
        db.commit()
    return {"deleted": True}

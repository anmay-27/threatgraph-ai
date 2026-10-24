"""Case management API. Local owner is explicit until account migration lands."""

from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, delete
from app.models.database import Analysis, Session, serialize
from app.models.cases import Case, CaseAsset, CaseEvent, now
from app.services.auth import principal, accessible
from app.core.config import settings

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


class CaseInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    status: Literal[
        "OPEN", "INVESTIGATING", "REVIEW_REQUIRED", "RESOLVED", "ARCHIVED"
    ] = "OPEN"
    severity: Literal["UNKNOWN", "LOW", "MODERATE", "HIGH", "CRITICAL"] = "UNKNOWN"
    tags: list[str] = Field(default_factory=list, max_length=20)
    final_verdict: str = Field(default="", max_length=5000)

    @field_validator("title")
    @classmethod
    def title_required(cls, value):
        if not value.strip():
            raise ValueError("A case title is required")
        return value.strip()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values):
        if any(len(v.strip()) > 50 for v in values):
            raise ValueError("Tags must be at most 50 characters")
        return list(dict.fromkeys(v.strip() for v in values if v.strip()))


class NoteInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Note cannot be blank")
        return value.strip()


def get_case(db, identifier):
    row = db.get(Case, identifier)
    if row is None or (
        settings.auth_required and row.owner_id != principal.get()["id"]
    ):
        raise HTTPException(404, "Case not found")
    return row


def event(db, case, action, content="", analysis_id=None):
    case.updated_at = now()
    db.add(
        CaseEvent(
            case_id=case.id, action=action, content=content, analysis_id=analysis_id
        )
    )


def case_dict(row):
    return {
        key: getattr(row, key)
        for key in (
            "id",
            "title",
            "description",
            "status",
            "severity",
            "tags",
            "final_verdict",
            "created_at",
            "updated_at",
        )
    }


@router.get("")
def list_cases(q: str = "", status: str = "", limit: int = 100, offset: int = 0):
    with Session() as db:
        statement = select(Case).order_by(Case.updated_at.desc(), Case.id)
        if settings.auth_required:
            statement = statement.where(Case.owner_id == principal.get()["id"])
        if q:
            statement = statement.where(Case.title.contains(q, autoescape=True))
        if status:
            statement = statement.where(Case.status == status)
        return [
            case_dict(row)
            for row in db.scalars(
                statement.offset(max(0, offset)).limit(min(100, max(1, limit)))
            )
        ]


@router.post("", status_code=201)
def create_case(body: CaseInput):
    with Session() as db:
        row = Case(**body.model_dump(), owner_id=principal.get()["id"])
        db.add(row)
        db.flush()
        event(db, row, "case_created", row.title)
        db.commit()
        return case_dict(row)


@router.get("/{identifier}")
def case_detail(identifier: str):
    with Session() as db:
        row = get_case(db, identifier)
        analyses = db.scalars(
            select(Analysis)
            .join(CaseAsset, CaseAsset.analysis_id == Analysis.id)
            .where(CaseAsset.case_id == identifier)
            .order_by(CaseAsset.created_at)
        ).all()
        events = db.scalars(
            select(CaseEvent)
            .where(CaseEvent.case_id == identifier)
            .order_by(CaseEvent.created_at, CaseEvent.id)
        ).all()
        graph = {"nodes": [], "edges": []}
        for analysis in analyses:
            source = (analysis.report or {}).get("graph", {})
            graph["nodes"].extend(
                {**n, "id": analysis.id + ":" + n["id"]}
                for n in source.get("nodes", [])
            )
            graph["edges"].extend(
                {
                    **e,
                    "id": analysis.id + ":" + e["id"],
                    "source": analysis.id + ":" + e["source"],
                    "target": analysis.id + ":" + e["target"],
                }
                for e in source.get("edges", [])
            )
        from app.models.intelligence import Entity, AnalysisEntity
        from app.services.intelligence import visible_entity, visible_count

        entity_rows = db.execute(
            select(Entity, AnalysisEntity.analysis_id)
            .join(AnalysisEntity)
            .where(AnalysisEntity.analysis_id.in_([a.id for a in analyses]))
        ).all()
        entities = {}
        for entity, aid in entity_rows:
            if entity.id not in entities:
                entities[entity.id] = {
                    **visible_entity(db, entity),
                    "investigation_count": visible_count(db, entity.id),
                }
                graph["nodes"].append(
                    {
                        "id": "entity:" + entity.id,
                        "type": entity.type.lower(),
                        "label": entity.display_value,
                    }
                )
            graph["edges"].append(
                {
                    "id": aid + ":entity:" + entity.id,
                    "source": "analysis:" + aid,
                    "target": "entity:" + entity.id,
                    "relation": "mentions",
                }
            )
        for a in analyses:
            graph["nodes"].append(
                {"id": "analysis:" + a.id, "type": "investigation", "label": a.name}
            )
            for n in (a.report or {}).get("graph", {}).get("nodes", [])[:1]:
                graph["edges"].append(
                    {
                        "id": "root:" + a.id,
                        "source": "analysis:" + a.id,
                        "target": a.id + ":" + n["id"],
                        "relation": "contains",
                    }
                )
        timeline = [
            {
                k: getattr(e, k)
                for k in ("id", "action", "content", "analysis_id", "created_at")
            }
            for e in events
        ]
        for a in analyses:
            timeline.extend(
                {
                    "id": a.id + ":step:" + str(i),
                    "action": "analysis_step",
                    "content": p["step"],
                    "analysis_id": a.id,
                    "created_at": p["timestamp"],
                }
                for i, p in enumerate(a.progress)
                if p.get("timestamp")
            )
        timeline.sort(key=lambda e: str(e["created_at"]))
        return {
            **case_dict(row),
            "entities": list(entities.values()),
            "analyses": [serialize(a) for a in analyses],
            "graph": graph,
            "timeline": timeline,
        }


@router.put("/{identifier}")
def update_case(identifier: str, body: CaseInput):
    with Session() as db:
        row = get_case(db, identifier)
        changed = [
            key
            for key, value in body.model_dump().items()
            if getattr(row, key) != value
        ]
        for key, value in body.model_dump().items():
            setattr(row, key, value)
        if changed:
            event(db, row, "case_updated", "Updated: " + ", ".join(changed))
        db.commit()
        return case_dict(row)


@router.post("/{identifier}/notes", status_code=201)
def add_note(identifier: str, body: NoteInput):
    with Session() as db:
        row = get_case(db, identifier)
        event(db, row, "note_added", body.content)
        db.commit()
        return {"saved": True}


@router.post("/{identifier}/analyses/{analysis_id}")
def attach_analysis(identifier: str, analysis_id: str):
    with Session() as db:
        row = get_case(db, identifier)
        analysis = db.get(Analysis, analysis_id)
        if analysis is None or not accessible(db, analysis_id):
            raise HTTPException(404, "Analysis not found")
        if not db.get(CaseAsset, (identifier, analysis_id)):
            db.add(CaseAsset(case_id=identifier, analysis_id=analysis_id))
            event(db, row, "analysis_added", analysis.name, analysis_id)
        db.commit()
        return {"saved": True}


@router.delete("/{identifier}/analyses/{analysis_id}")
def detach_analysis(identifier: str, analysis_id: str):
    with Session() as db:
        row = get_case(db, identifier)
        link = db.get(CaseAsset, (identifier, analysis_id))
        if link:
            db.delete(link)
            event(db, row, "analysis_removed", analysis_id, analysis_id)
        db.commit()
        return {"removed": True}


@router.delete("/{identifier}")
def delete_case(identifier: str):
    with Session() as db:
        row = get_case(db, identifier)
        db.execute(delete(CaseAsset).where(CaseAsset.case_id == identifier))
        db.execute(delete(CaseEvent).where(CaseEvent.case_id == identifier))
        db.delete(row)
        db.commit()
        return {"deleted": True, "analyses_preserved": True}

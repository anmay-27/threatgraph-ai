"""Deterministic entity extraction. Occurrence is not evidence of maliciousness."""

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qs
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.database import Analysis, Session, serialize
from app.models.cases import Case, CaseAsset
from app.models.intelligence import Entity, AnalysisEntity
from app.services.auth import accessible, allowed_analysis_ids, principal
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["intelligence"])


def extract_text(text):
    result = set()
    for raw in re.findall(r'https?://[^\s<>"\x27]+', text[:100000], re.I):
        raw = raw.rstrip(".,;!?)")
        try:
            p = urlsplit(raw)
            host = (p.hostname or "").encode("idna").decode().lower().rstrip(".")
            if not host or p.username or p.password:
                continue
            port = p.port
            netloc = "[" + host + "]" if ":" in host else host
            if port and (p.scheme.lower(), port) not in [("https", 443), ("http", 80)]:
                netloc += ":" + str(port)
            value = urlunsplit((p.scheme.lower(), netloc, p.path or "/", p.query, ""))
            if len(value) <= 2048:
                result.add(("URL", value))
                result.add(("DOMAIN", host))
        except (ValueError, UnicodeError):
            continue
    non_url_text = re.sub(r'https?://[^\s<>"\x27]+', "", text[:100000], flags=re.I)
    for email in re.findall(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", non_url_text):
        local, host = email.rsplit("@", 1)
        result.add(("EMAIL", local + "@" + host.lower()))
        result.add(("DOMAIN", host.lower()))
    for raw in re.findall(r"(?<!\w)\+\d[\d ()-]{7,19}\d(?!\w)", text[:100000]):
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 15:
            result.add(("PHONE_NUMBER", "+" + digits))
    for uri in re.findall(r'upi://pay\?[^\s<>"\x27]+', text[:100000], re.I):
        payee = parse_qs(urlsplit(uri).query).get("pa", [""])[0]
        if re.fullmatch(r"[\w.+-]+@[\w.-]+", payee):
            result.add(("UPI_ID", payee.lower()))
    return sorted(result)


def extract_report(row):
    report = row.report or {}
    pairs = set(extract_text(row.name))
    if row.sha256:
        pairs.add(("FILE_HASH", row.sha256.lower()))
    if row.input_type != "url":
        pairs.add(("FILENAME", row.name[:2048]))
    mapping = {
        "url": "URL",
        "domain": "DOMAIN",
        "brand": "BRAND",
        "qr_code": "QR_DESTINATION",
        "email": "EMAIL",
    }
    for n in report.get("graph", {}).get("nodes", []):
        value = n.get("label", "")
        if n.get("type") in mapping and value and len(value) <= 2048:
            kind = mapping[n["type"]]
            if kind == "URL":
                pairs.update(extract_text(value))
            else:
                pairs.add(
                    (kind, value.lower() if kind in ("DOMAIN", "BRAND") else value)
                )
    for asset in report.get("assets", []):
        if asset.get("sha256"):
            pairs.add(("FILE_HASH", asset["sha256"].lower()))
    for evidence in report.get("evidence", []):
        meta = evidence.get("metadata", {})
        for key in ("text", "ocr", "payload", "sender", "reply_to"):
            if isinstance(meta.get(key), str):
                pairs.update(extract_text(meta[key]))
        for brand in meta.get("brands", []):
            if isinstance(brand, str):
                pairs.add(("BRAND", brand.lower()))
    return sorted(pairs)[:500]


def index_analysis(db, row):
    """Idempotent, concurrent-safe upserts; never mutate the original report."""
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(delete(AnalysisEntity).where(AnalysisEntity.analysis_id == row.id))
    for kind, value in extract_report(row):
        identifier = hashlib.sha256((kind + "\0" + value).encode()).hexdigest()
        statement = insert(Entity).values(
            id=identifier,
            type=kind,
            normalized_value=value,
            display_value=value,
            first_seen=row.created_at,
            last_seen=row.created_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "first_seen": func.min(Entity.first_seen, row.created_at)
                if db.bind.dialect.name == "sqlite"
                else func.least(Entity.first_seen, row.created_at),
                "last_seen": func.max(Entity.last_seen, row.created_at)
                if db.bind.dialect.name == "sqlite"
                else func.greatest(Entity.last_seen, row.created_at),
            },
        )
        db.execute(statement)
        db.add(AnalysisEntity(analysis_id=row.id, entity_id=identifier))


def entity_dict(row):
    return {
        k: getattr(row, k)
        for k in (
            "id",
            "type",
            "display_value",
            "normalized_value",
            "first_seen",
            "last_seen",
        )
    }


@router.get("/entities/search")
def search_entities(q: str = "", type: str = "", limit: int = 100):
    with Session() as db:
        query = (
            select(Entity, func.count(AnalysisEntity.analysis_id))
            .join(AnalysisEntity)
            .group_by(Entity.id)
            .order_by(Entity.last_seen.desc(), Entity.id)
        )
        if settings.auth_required:
            query = query.where(AnalysisEntity.analysis_id.in_(allowed_analysis_ids()))
        if q:
            query = query.where(Entity.normalized_value.contains(q, autoescape=True))
        if type:
            query = query.where(Entity.type == type)
        return [
            {**visible_entity(db, e), "investigation_count": count}
            for e, count in db.execute(query.limit(min(100, max(1, limit))))
        ]


@router.get("/entities/{identifier}")
def entity_detail(identifier: str):
    with Session() as db:
        row = db.get(Entity, identifier)
        if not row:
            raise HTTPException(404, "Entity not found")
        query = (
            select(Analysis)
            .join(AnalysisEntity)
            .where(AnalysisEntity.entity_id == identifier)
        )
        if settings.auth_required:
            query = query.where(Analysis.id.in_(allowed_analysis_ids()))
        analyses = db.scalars(query.order_by(Analysis.created_at.desc())).all()
        if not analyses:
            raise HTTPException(404, "Entity not found")
        aids = [a.id for a in analyses]
        case_query = select(Case).join(CaseAsset).where(CaseAsset.analysis_id.in_(aids))
        if settings.auth_required:
            case_query = case_query.where(Case.owner_id == principal.get()["id"])
        cases = db.scalars(case_query.distinct()).all()
        return {
            **visible_entity(db, row),
            "investigation_count": len(analyses),
            "analyses": [serialize(a) for a in analyses],
            "cases": [{"id": c.id, "title": c.title} for c in cases],
            "limitation": "A repeated entity or shared domain does not establish maliciousness or common ownership.",
        }


@router.get("/analyses/{identifier}/entities")
def analysis_entities(identifier: str):
    with Session() as db:
        if not db.get(Analysis, identifier) or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        entities = db.scalars(
            select(Entity)
            .join(AnalysisEntity)
            .where(AnalysisEntity.analysis_id == identifier)
        ).all()
        return [
            {**visible_entity(db, e), "investigation_count": visible_count(db, e.id)}
            for e in entities
        ]


@router.get("/intelligence/graph")
def intelligence_graph(q: str = "", limit: int = 100):
    with Session() as db:
        query = (
            select(Entity)
            .where(Entity.normalized_value.contains(q, autoescape=True))
            .order_by(Entity.last_seen.desc(), Entity.id)
            .limit(min(100, max(1, limit)))
        )
        if settings.auth_required:
            query = query.where(
                Entity.id.in_(
                    select(AnalysisEntity.entity_id).where(
                        AnalysisEntity.analysis_id.in_(allowed_analysis_ids())
                    )
                )
            )
        entities = db.scalars(query).all()
        nodes = [
            {"id": e.id, "type": e.type.lower(), "label": e.display_value}
            for e in entities
        ]
        link_query = (
            select(AnalysisEntity, Analysis)
            .join(Analysis, Analysis.id == AnalysisEntity.analysis_id)
            .where(AnalysisEntity.entity_id.in_([e.id for e in entities]))
        )
        if settings.auth_required:
            link_query = link_query.where(Analysis.id.in_(allowed_analysis_ids()))
        links = db.execute(
            link_query.order_by(Analysis.created_at.desc()).limit(500)
        ).all()
        seen = set()
        edges = []
        for link, a in links:
            aid = "analysis:" + a.id
            if aid not in seen:
                nodes.append(
                    {
                        "id": aid,
                        "type": "investigation",
                        "label": a.name,
                        "severity": (a.report or {})
                        .get("risk_level", "unknown")
                        .lower(),
                    }
                )
                seen.add(aid)
            edges.append(
                {
                    "id": aid + ":" + link.entity_id,
                    "source": aid,
                    "target": link.entity_id,
                    "relation": link.relation,
                }
            )
        return {
            "nodes": nodes,
            "edges": edges,
            "bounded": True,
            "limits": {"entities": min(100, max(1, limit)), "occurrences": 500},
        }


def visible_entity(db, row):
    result = entity_dict(row)
    if settings.auth_required:
        result["first_seen"], result["last_seen"] = db.execute(
            select(func.min(Analysis.created_at), func.max(Analysis.created_at))
            .join(AnalysisEntity)
            .where(
                AnalysisEntity.entity_id == row.id,
                Analysis.id.in_(allowed_analysis_ids()),
            )
        ).one()
    return result


def visible_count(db, identifier):
    query = (
        select(func.count())
        .select_from(AnalysisEntity)
        .where(AnalysisEntity.entity_id == identifier)
    )
    if settings.auth_required:
        query = query.where(AnalysisEntity.analysis_id.in_(allowed_analysis_ids()))
    return db.scalar(query)

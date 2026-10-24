import asyncio
import hashlib
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from app.core.config import settings
from app.core.fetch import normalize_url
from app.models.database import Analysis, Base, Session, engine, serialize
from app.analyzers.file.inspect import detect_mime
from app.services.registry import registry
from app.services.cases import router as cases_router
from app.services.intelligence import router as intelligence_router
from app.services.reports import router as reports_router
from app.services.auth import (
    router as auth_router,
    authenticate,
    principal,
    own_analysis,
    accessible,
    scope,
)
from app.services.privacy import router as privacy_router
from app.services.operations import router as operations_router
from app.services.feedback import router as feedback_router
from app.services.jobs import router as jobs_router

executor = ThreadPoolExecutor(max_workers=2)


@asynccontextmanager
async def lifespan(app):
    global executor
    executor = ThreadPoolExecutor(max_workers=2)
    # Local SQLite convenience. Production uses Alembic before server startup.
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)

    async def retention_loop():
        from app.workers.tasks import cleanup

        while True:
            await asyncio.to_thread(cleanup.run)
            await asyncio.sleep(3600)

    retention = (
        asyncio.create_task(retention_loop()) if settings.task_always_eager else None
    )
    yield
    if retention:
        retention.cancel()
        with suppress(asyncio.CancelledError):
            await retention
    executor.shutdown(wait=True)


app = FastAPI(title="ThreatGraph AI", version="0.1.0", lifespan=lifespan)
app.include_router(cases_router)
app.include_router(intelligence_router)
app.include_router(reports_router)
app.include_router(auth_router)
app.include_router(privacy_router)
app.include_router(operations_router)
app.include_router(feedback_router)
app.include_router(jobs_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
requests = defaultdict(deque)


@app.middleware("http")
async def guard(request: Request, call_next):
    token = None
    if settings.auth_required and request.url.path.startswith("/api/v1/"):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin not in settings.allowed_origins.split(","):
                if not request.headers.get('authorization','').startswith('Bearer '):
                    return JSONResponse({"detail": "Origin is not allowed"}, 403)
                try:authenticate(request)
                except HTTPException as exc:return JSONResponse({'detail':exc.detail},exc.status_code)
        if (
            request.url.path
            not in ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/health")
            and request.method != "OPTIONS"
        ):
            try:
                user = authenticate(request)
                token = principal.set(user)
                if request.url.path.startswith(
                    ("/api/v1/cases", "/api/v1/entities", "/api/v1/intelligence")
                ) and user["role"] not in ("ANALYST", "ADMIN"):
                    principal.reset(token)
                    return JSONResponse({"detail": "Analyst role required"}, 403)
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, exc.status_code)
    if request.method == "POST":
        address = (
            "account:" + principal.get()["id"]
            if settings.auth_required and token is not None
            else request.client.host if request.client else "unknown"
        )
        bucket = requests[address]
        now = time.monotonic()
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= 12:
            return JSONResponse(
                {"detail": "Submission limit reached; retry in one minute."}, 429
            )
        bucket.append(now)
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > (settings.max_upload_mb + 1) * 1024 * 1024:
                    return JSONResponse({"detail": "Upload exceeds size limit"}, 413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, 400)
        # Count ASGI chunks too: Content-Length is untrusted or absent.
        consumed = 0
        original_receive = request._receive

        async def limited_receive():
            nonlocal consumed
            message = await original_receive()
            consumed += len(message.get("body", b""))
            if consumed > (settings.max_upload_mb + 1) * 1024 * 1024:
                raise HTTPException(413, "Upload exceeds size limit")
            return message

        request._receive = limited_receive
    try:
        response = await call_next(request)
    finally:
        if token is not None:
            principal.reset(token)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


class URLInput(BaseModel):
    url: str = Field(min_length=8, max_length=8192)


class MessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=100000)
    title: str = Field(default="Suspicious message", min_length=1, max_length=200)


def submit_text(body, email=False):
    if not body.text.strip():
        raise HTTPException(422, "Message is empty")
    identifier = str(uuid4())
    path = settings.storage_dir / identifier
    data = body.text.encode("utf-8")
    path.write_bytes(data)
    with Session() as db:
        row = Analysis(
            id=identifier,
            input_type="email" if email else "message",
            name=body.title + (".eml" if email else ".txt"),
            path=str(path.resolve()),
            mime="message/rfc822" if email else "text/plain",
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
        )
        db.add(row)
        own_analysis(db, row)
        db.commit()
    queue(row)
    return {"id": identifier, "state": "QUEUED"}


@app.post("/api/v1/analyze/message", status_code=202)
def analyze_message(body: MessageInput):
    return submit_text(body)


@app.post("/api/v1/analyze/email", status_code=202)
def analyze_email(body: MessageInput):
    return submit_text(body, email=True)


def queue(row):
    try:
        if settings.task_always_eager:
            from app.services.investigation import run

            executor.submit(run, row.id)
        else:
            from app.workers.tasks import investigate

            investigate.apply_async(args=[row.id], retry=False)
    except Exception:
        with Session() as db:
            stored = db.get(Analysis, row.id)
            stored.state = "FAILED"
            stored.error = "Job queue unavailable. Start Redis and the worker."
            db.commit()
        raise HTTPException(503, "Job queue unavailable")


@app.post("/api/v1/analyze/url", status_code=202)
def analyze_url(body: URLInput):
    try:
        url = normalize_url(body.url.strip())
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    with Session() as db:
        row = Analysis(input_type="url", name=url)
        db.add(row)
        own_analysis(db, row)
        db.commit()
    queue(row)
    return {"id": row.id, "state": "QUEUED"}


@app.post("/api/v1/analyze/file", status_code=202)
async def analyze_file(file: UploadFile = File(...)):
    identifier = str(uuid4())
    path = settings.storage_dir / identifier
    size = 0
    digest = hashlib.sha256()
    try:
        with path.open("wb") as out:
            while block := await file.read(65536):
                size += len(block)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, "Upload exceeds size limit")
                digest.update(block)
                out.write(block)
        if size == 0:
            raise HTTPException(422, "Empty file")
        mime = detect_mime(path.read_bytes()[:8192])
        kind = (
            mime.split("/")[0]
            if mime.startswith(("image/", "audio/", "video/"))
            else "file"
        )
        name = (file.filename or "upload").replace("\\", "/").split("/")[-1][:200]
        with Session() as db:
            row = Analysis(
                id=identifier,
                input_type=kind,
                name=name,
                sha256=digest.hexdigest(),
                mime=mime,
                size=size,
                path=str(path.resolve()),
            )
            db.add(row)
            own_analysis(db, row)
            db.commit()
        queue(row)
        return {"id": row.id, "state": "QUEUED"}
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


def get_row(identifier):
    with Session() as db:
        row = db.get(Analysis, identifier)
        if not row or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        return row


@app.get("/api/v1/analyses/{identifier}")
def analysis(identifier: str):
    return serialize(get_row(identifier))


@app.get("/api/v1/analyses/{identifier}/status")
def status(identifier: str):
    row = get_row(identifier)
    return {
        "id": row.id,
        "state": row.state,
        "progress": row.progress,
        "error": row.error,
    }


@app.get("/api/v1/analyses/{identifier}/graph")
def graph(identifier: str):
    return (get_row(identifier).report or {}).get("graph", {"nodes": [], "edges": []})


@app.get("/api/v1/analyses/{identifier}/evidence")
def evidence(identifier: str):
    return (get_row(identifier).report or {}).get("evidence", [])


@app.get("/api/v1/analyses/{identifier}/media")
def media(identifier: str):
    row = get_row(identifier)
    if not row.path or not Path(row.path).is_file():
        raise HTTPException(410, "Original file expired or unavailable")
    if row.input_type not in ("image", "audio", "video") or row.mime == "image/svg+xml":
        raise HTTPException(415, "This file cannot be previewed")
    return FileResponse(
        row.path,
        media_type=row.mime,
        headers={"Content-Security-Policy": "default-src 'none'; sandbox"},
    )


@app.get("/api/v1/history")
def history(
    q: str = "",
    input_type: str = "",
    risk: str = "",
    verdict: str = "",
    after: datetime | None = None,
    limit: int = 100,
):
    with Session() as db:
        statement = scope(select(Analysis)).order_by(Analysis.created_at.desc())
        if q:
            statement = statement.where(Analysis.name.contains(q, autoescape=True))
        if input_type:
            statement = statement.where(Analysis.input_type == input_type)
        if after:
            statement = statement.where(Analysis.created_at >= after)
        rows = db.scalars(statement.limit(min(max(limit, 1), 500))).all()
        return [
            serialize(row)
            for row in rows
            if (not risk or (row.report or {}).get("risk_level") == risk)
            and (not verdict or (row.report or {}).get("verdict") == verdict)
        ]


@app.get("/api/v1/dashboard")
def dashboard():
    from collections import Counter

    with Session() as db:
        rows = db.scalars(scope(select(Analysis))).all()
    return {
        "total": len(rows),
        "high_risk": sum(
            (r.report or {}).get("risk_level") in ("HIGH", "CRITICAL") for r in rows
        ),
        "threats_detected": sum(bool((r.report or {}).get("categories")) for r in rows),
        "inconclusive": sum(
            (r.report or {}).get("verdict") == "INCONCLUSIVE" for r in rows
        ),
        "types": dict(Counter(r.input_type for r in rows)),
        "risks": dict(
            Counter((r.report or {}).get("risk_level", "PENDING") for r in rows)
        ),
        "categories": dict(
            Counter(c for r in rows for c in (r.report or {}).get("categories", []))
        ),
    }


@app.get("/api/v1/models")
def models():
    return registry()


@app.get("/api/v1/health")
def health():
    from app.analyzers.file.antivirus import daemon_status
    with Session() as db:
        db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "privacy_mode": settings.privacy_mode,
        "external_reputation": settings.enable_external_reputation,
        "queue_mode": "local-thread-development"
        if settings.task_always_eager
        else "celery",
        "max_upload_mb": settings.max_upload_mb,
        "malware_scanner": daemon_status(settings.clamav_host),
    }

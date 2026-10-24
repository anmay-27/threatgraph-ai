from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, text
from pathlib import Path
import shutil
from app.models.database import Session, Analysis
from app.services.auth import principal, Account
from app.services.registry import registry
from app.core.config import settings
from app.analyzers.file.antivirus import daemon_status

router = APIRouter(prefix="/api/v1/admin", tags=["operations"])


def admin():
    if principal.get()["role"] != "ADMIN":
        raise HTTPException(403, "Administrator role required")


@router.get("/health")
def operations():
    admin()
    with Session() as db:
        db.execute(text("SELECT 1"))
        counts = dict(
            db.execute(
                select(Analysis.state, func.count()).group_by(Analysis.state)
            ).all()
        )
    redis = "not used in local mode"
    if not settings.task_always_eager:
        try:
            from redis import Redis

            redis = (
                "available"
                if Redis.from_url(
                    settings.redis_url, socket_connect_timeout=2, socket_timeout=2
                ).ping()
                else "unavailable"
            )
        except Exception:
            redis = "unavailable"
    disk = shutil.disk_usage(settings.storage_dir)
    return {
        "api": "available",
        "database": "available",
        "redis": redis,
        "queue_mode": "local thread executor"
        if settings.task_always_eager
        else "celery",
        "jobs": counts,
        "models": registry(),
        "disk": {"total": disk.total, "free": disk.free},
        "privacy_mode": settings.privacy_mode,
        "external_reputation": settings.enable_external_reputation,
        "clamav": daemon_status(settings.clamav_host),
        "workers": "Live worker heartbeats not implemented",
    }


@router.get("/users")
def users():
    admin()
    with Session() as db:
        return [
            {"id": a.id, "email": a.email, "role": a.role}
            for a in db.scalars(select(Account).limit(500))
        ]

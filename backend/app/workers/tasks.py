from datetime import datetime, timedelta, timezone
from pathlib import Path
from celery import Celery
from sqlalchemy import select
from app.core.config import settings
from app.models.database import Analysis, Session

celery = Celery("threatgraph", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=270,
    broker_connection_retry_on_startup=True,
    beat_schedule={"retention-cleanup": {"task": "cleanup", "schedule": 3600}},
)


@celery.task(name="investigate")
def investigate(identifier):
    from app.services.investigation import run

    run(identifier)


@celery.task(name="cleanup")
def cleanup():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.retention_hours)
    with Session() as db:
        rows = db.scalars(
            select(Analysis).where(
                Analysis.created_at < cutoff,
                Analysis.state.in_(["COMPLETED", "PARTIAL", "FAILED", "CANCELLED"]),
            )
        ).all()
        for row in rows:
            if row.path:
                path = Path(row.path).resolve()
                if path.is_relative_to(settings.storage_dir.resolve()):
                    path.unlink(missing_ok=True)
                row.path = None
        db.commit()

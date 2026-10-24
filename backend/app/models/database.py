from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    input_type: Mapped[str] = mapped_column(default="file")
    name: Mapped[str]
    sha256: Mapped[str | None] = mapped_column(index=True)
    mime: Mapped[str | None]
    size: Mapped[int] = mapped_column(default=0)
    path: Mapped[str | None]
    state: Mapped[str] = mapped_column(default="QUEUED", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    progress: Mapped[list] = mapped_column(JSON, default=list)
    report: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None]


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


# Evidence entities are normalized by analysis, with versioned JSON payloads.
def entity(name: str):
    return type(
        name.title().replace("_", ""),
        (Base,),
        {
            "__tablename__": name,
            "__annotations__": {
                "id": Mapped[str],
                "analysis_id": Mapped[str],
                "payload": Mapped[dict],
            },
            "id": mapped_column(String(100), primary_key=True),
            "analysis_id": mapped_column(
                ForeignKey("analyses.id", ondelete="CASCADE"), index=True
            ),
            "payload": mapped_column(JSON),
        },
    )


ENTITIES = {
    name: entity(name)
    for name in (
        "assets",
        "detector_results",
        "evidence",
        "evidence_conflicts",
        "graph_nodes",
        "graph_edges",
        "fraud_scenarios",
    )
}
engine = create_engine(
    settings.database_url,
    **(
        {"connect_args": {"check_same_thread": False}}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
)
Session = sessionmaker(engine, expire_on_commit=False)


def serialize(row: Analysis) -> dict:
    result = {
        key: getattr(row, key)
        for key in (
            "id",
            "input_type",
            "name",
            "sha256",
            "mime",
            "size",
            "state",
            "created_at",
            "progress",
            "report",
            "error",
        )
    }
    if row.input_type == 'url' and row.report:
        from app.services.url_summary import summarize_url
        result['report'] = {**row.report, 'url_summary': summarize_url(row.name, row.report)}
    return result

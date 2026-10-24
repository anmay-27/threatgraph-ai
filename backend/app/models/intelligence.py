from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base
from app.models.cases import now


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("type", "normalized_value", name="uq_entity_value"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    normalized_value: Mapped[str] = mapped_column(String(2048))
    display_value: Mapped[str] = mapped_column(String(2048))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AnalysisEntity(Base):
    __tablename__ = "analysis_entities"
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True
    )
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    relation: Mapped[str] = mapped_column(default="mentions")
    confidence: Mapped[float] = mapped_column(default=1.0)

from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    asset_id: str
    source: str
    category: str
    label: str
    score: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(default=0, ge=0, le=1)
    uncertainty: float = Field(default=1, ge=0, le=1)
    severity: Literal["info", "low", "moderate", "high", "critical"] = "info"
    explanation: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_version: str = "rules-1.0"
    # Only comparable hypotheses can contradict one another.
    hypothesis: str | None = None


def finding(
    asset_id: str,
    source: str,
    category: str,
    label: str,
    explanation: str,
    score: float | None = None,
    confidence: float = 0.7,
    **kwargs,
) -> Evidence:
    severity = (
        "info"
        if score is None or category in {"synthetic_media", "manipulation", "provenance"} or kwargs.get("metadata", {}).get("risk_eligible") is False
        else (
            "critical"
            if score >= 0.75
            else "high"
            if score >= 0.5
            else "moderate"
            if score >= 0.25
            else "low"
        )
    )
    return Evidence(
        asset_id=asset_id,
        source=source,
        category=category,
        label=label,
        explanation=explanation,
        score=score,
        confidence=confidence if score is not None else 0,
        uncertainty=1 - confidence if score is not None else 1,
        severity=severity,
        **kwargs,
    )

from collections import defaultdict
from itertools import combinations
from app.schemas.evidence import Evidence


def conflicts(evidence: list[Evidence]) -> list[dict]:
    result = []
    for a, b in combinations(evidence, 2):
        if a.asset_id != b.asset_id or not a.hypothesis or a.hypothesis != b.hypothesis:
            continue
        if a.score is None or b.score is None or min(a.confidence, b.confidence) < 0.6:
            continue
        if abs(a.score - b.score) >= 0.6:
            result.append(
                {
                    "id": f"{a.id}:{b.id}",
                    "evidence_a": a.id,
                    "evidence_b": b.id,
                    "type": "audio_visual_conflict"
                    if {a.source, b.source} == {"audio_detector", "video_detector"}
                    else "contradiction",
                    "severity": "high",
                    "explanation": f"{a.source} and {b.source} disagree about {a.hypothesis}; manual verification is recommended.",
                }
            )
    return result


def fuse(evidence: list[Evidence], conflict_list: list[dict], incomplete=False) -> dict:
    scored = [e for e in evidence if e.score is not None and e.confidence > 0]
    # Origin and authenticity are separate hypotheses from malicious intent.
    security = [e for e in scored if e.hypothesis != "synthetic_media" and e.category not in {"synthetic_media", "manipulation", "provenance"}]
    excluded = [e for e in security if e.source == "url_detector" and e.metadata.get("deployment_status") != "validated_external"]
    security = [e for e in security if e not in excluded and e.metadata.get("risk_eligible") is not False]
    # Correlated findings within a detector/category do not multiply risk.
    groups = defaultdict(list)
    for e in security:
        groups[(e.asset_id, e.category)].append(e)
    contributions = [
        {
            "asset_id": key[0],
            "category": key[1],
            "score": max(e.score * e.confidence for e in items),
            "evidence_ids": [e.id for e in items],
        }
        for key, items in groups.items()
    ]
    # Transparent conservative rule baseline; never represented as calibrated ML.
    risk = (
        round(100 * max((c["score"] for c in contributions), default=0))
        if security
        else None
    )
    method = "security-indicators-only-v3 (uncalibrated)"
    from app.services.registry import registry, load_tabular
    from app.core.config import settings
    from app.fusion.features import vector

    record = next(r for r in registry() if r["name"] == "fusion")
    if record["available"] and security and record.get("risk_semantics") == "malicious_intent":
        try:
            path = settings.model_dir / "fusion" / record["file_path"]
            model = load_tabular(str(path), path.stat().st_mtime_ns)
            risk = round(
                100
                * float(model.predict_proba([vector(security, conflict_list)])[0, 1])
            )
            method = "calibrated-learned-fusion:" + record["version"]
        except Exception:
            incomplete = True
            method += "; learned fusion unavailable"
    uncertainty = (
        max(0.35, sum(e.uncertainty for e in security) / len(security)) if security else 1.0
    )
    if incomplete:
        uncertainty = max(uncertainty, 0.65)
    if conflict_list:
        uncertainty = max(uncertainty, 0.85)
    if any(e.metadata.get("ood") == "possibly_out_of_distribution" for e in evidence):
        uncertainty = max(uncertainty, 0.9)
    inconclusive = uncertainty >= 0.65 or risk is None
    return {
        "risk_score": risk,
        "risk_level": "UNKNOWN"
        if risk is None
        else "LOW"
        if risk < 25
        else "MODERATE"
        if risk < 50
        else "HIGH"
        if risk < 75
        else "CRITICAL",
        "confidence": round(1 - uncertainty, 3),
        "uncertainty": round(uncertainty, 3),
        "uncertainty_level": "HIGH"
        if uncertainty >= 0.65
        else "MEDIUM"
        if uncertainty >= 0.3
        else "LOW",
        "verdict": "INCONCLUSIVE"
        if inconclusive
        else "THREAT_INDICATORS"
        if risk >= 50
        else "LIMITED_INDICATORS",
        "fusion_method": method,
        "contributions": contributions,
        "excluded_risk_evidence": [e.id for e in excluded],
        "risk_explanation": "The experimental URL classifier is retained as a screening signal, but excluded from security-risk scoring because field reliability is not established. No other scored security evidence is available; this does not establish that the URL is safe." if excluded and not security else "Risk uses scored security evidence. Experimental URL classifier outputs do not contribute to the risk score.",
        "recommendations": [
            "Manual verification recommended."
            if inconclusive
            else "Review the evidence before trusting this content.",
            "Verify the source through an independently obtained official channel.",
            "Do not enter credentials or payment information into suspicious pages.",
        ],
    }

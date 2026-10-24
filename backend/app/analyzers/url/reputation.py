"""Optional URL-only reputation: never uploads file bytes."""

import requests
from app.core.config import settings
from app.schemas.evidence import finding


def reputation(url, asset):
    if settings.privacy_mode or not settings.enable_external_reputation:
        return []
    if not settings.urlhaus_auth_key:
        return [
            finding(
                asset,
                "reputation",
                "reputation",
                "unavailable",
                "URLhaus requires an Auth-Key; no external query was sent.",
            )
        ]
    try:
        response = requests.post(
            "https://urlhaus-api.abuse.ch/v1/url/",
            headers={"Auth-Key": settings.urlhaus_auth_key},
            data={"url": url},
            timeout=8,
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("query_status") == "ok":
            return [
                finding(
                    asset,
                    "reputation",
                    "reputation",
                    "urlhaus_match",
                    "URLhaus reports this URL in its malware URL database.",
                    0.95,
                    0.95,
                    metadata={
                        "url_status": payload.get("url_status"),
                        "threat": payload.get("threat"),
                    },
                )
            ]
        if payload.get("query_status") == "no_results":
            return [
                finding(
                    asset,
                    "reputation",
                    "reputation",
                    "no_result",
                    "No URLhaus record found; this is not a safety verdict.",
                )
            ]
        raise ValueError("Unexpected reputation response")
    except Exception:
        return [
            finding(
                asset,
                "reputation",
                "reputation",
                "unavailable",
                "External reputation query did not complete.",
            )
        ]

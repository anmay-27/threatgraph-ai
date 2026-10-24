from app.analyzers.url.brands import lexical_findings
from app.analyzers.url.page import inspect_page
from app.fusion.engine import fuse
from app.schemas.evidence import finding


def test_google_meet_auth_redirect_is_not_phishing_by_password_presence():
    original = lexical_findings("https://meet.google.com/home", "submitted")[0]
    assert original.metadata["listed_first_party_domains"] == [
        {"brand": "google", "base_domain": "google.com"}
    ]
    html = b'<title>Sign in - Google Accounts</title><form action="https://accounts.google.com/v3/signin/identifier" method="post"><input type="password" name="Passwd"></form>'
    _, findings, _ = inspect_page(html, "https://accounts.google.com/v3/signin/identifier", "page")
    password = next(e for e in findings if e.label == "password_form")
    assert password.score is None
    assert not any(e.label == "credential_destination_mismatch" for e in findings)
    experimental = finding("submitted", "url_detector", "phishing", "phishing_probability", "Experimental lexical score", .99, .35, metadata={"deployment_status": "experimental"})
    report = fuse([original, *findings, experimental], [])
    assert report["risk_score"] is None
    assert report["risk_level"] == "UNKNOWN"
    assert experimental.id in report["excluded_risk_evidence"]


def test_google_lookalike_is_not_first_party_match():
    result = lexical_findings("https://meet.google.com.evil.example/login", "asset")[0]
    assert result.metadata["listed_first_party_domains"] == []

from app.schemas.evidence import finding
from app.fusion.engine import fuse, conflicts
from app.threat_graph.graph import ThreatGraph, infer_scenarios
from app.analyzers.url.page import inspect_page


def test_no_evidence_is_not_safe():
    result = fuse([], [])
    assert result["risk_score"] is None
    assert result["verdict"] == "INCONCLUSIVE"


def test_missing_provenance_neutral():
    evidence = [finding("a", "c2pa", "provenance", "not_present", "No credential")]
    assert conflicts(evidence) == []
    assert fuse(evidence, [])["risk_score"] is None


def test_conflict_requires_same_asset_and_hypothesis():
    a = finding(
        "a",
        "image_detector",
        "synthetic_media",
        "synthetic",
        "test",
        0.95,
        0.9,
        hypothesis="synthetic_media",
    )
    b = finding(
        "a",
        "c2pa",
        "synthetic_media",
        "camera",
        "test",
        0.02,
        0.95,
        hypothesis="synthetic_media",
    )
    c = conflicts([a, b])
    assert len(c) == 1
    assert fuse([a, b], c)["uncertainty"] >= 0.85
    assert fuse([a, b], c)["risk_score"] is None
    b.asset_id = "other"
    assert not conflicts([a, b])


def test_risk_not_confidence():
    evidence = [finding("a", "web", "phishing", "credential", "off-domain", 0.9, 0.9)]
    complete = fuse(evidence, [])
    partial = fuse(evidence, [], True)
    assert complete["risk_score"] == partial["risk_score"] == 81
    assert partial["confidence"] < complete["confidence"]


def test_experimental_url_score_never_establishes_threat_or_safety():
    for score in (.001, .999):
        model = finding("a", "url_detector", "phishing", "phishing_probability", "experimental", score, .35, metadata={"deployment_status": "experimental", "risk_eligible": False})
        result = fuse([model], [], True)
        assert result['risk_score'] is None
        assert result['risk_level'] == 'UNKNOWN'
        assert result['excluded_risk_evidence'] == [model.id]
        assert model.severity == 'info'
        page = finding("a", "web", "phishing", "credential", "off-domain", .9, .9)
        assert fuse([model, page], [])["risk_score"] == 81


def test_embedded_resource_mismatch_does_not_raise_page_risk():
    embedded = finding("image", "file_inspector", "file_security", "extension_mismatch", "Embedded image mismatch", .4, .7, metadata={"risk_eligible": False})
    assert fuse([embedded], [])["risk_score"] is None
    uploaded = finding("upload", "file_inspector", "file_security", "extension_mismatch", "Uploaded file mismatch", .4, .7)
    assert fuse([uploaded], [])["risk_score"] == 28


def test_ai_origin_does_not_inflate_security_risk():
    ai = finding("a", "image_detector", "synthetic_media", "synthetic", "AI origin", .99, .99, hypothesis="synthetic_media")
    phishing = finding("a", "web", "phishing", "credential", "off-domain", .9, .9)
    assert fuse([ai], [])["risk_score"] is None
    assert fuse([ai, phishing], [])["risk_score"] == fuse([phishing], [])["risk_score"] == 81


def test_static_phishing():
    html = b'<html><title>Account</title><body>Microsoft account suspended. Verify immediately<form action="https://collector.example/submit"><input type="password"></form></body></html>'
    page, evidence, assets = inspect_page(html, "https://login.example/", "a")
    assert page["password_fields"] == 1
    assert any(e.label == "credential_destination_mismatch" for e in evidence)
    graph = ThreatGraph()
    graph.nodes = [{"id": "a", "type": "webpage", "label": "test"}]
    assert (
        infer_scenarios(evidence, graph)[0]["label"] == "Potential credential phishing"
    )


def test_graph_bounds():
    g = ThreatGraph(2)
    a = g.node("url", "a")
    b = g.node("url", "b")
    c = g.node("url", "c")
    g.edge(a, b, "redirects_to")
    g.edge(b, c, "links_to")
    assert len(g.nodes) == 2 and len(g.edges) == 1

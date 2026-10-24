from app.analyzers.message import inspect_message, parse_email, email_findings
from app.services.scenarios import additional_scenarios


def test_recruitment_requires_both_offer_and_fee():
    assert not additional_scenarios(inspect_message("A job offer for you", "a"))
    findings = inspect_message("Job offer: pay a registration fee immediately", "a")
    scenarios = additional_scenarios(findings)
    assert scenarios[0]["scenario_name"] == "recruitment_scam"
    assert set(scenarios[0]["evidence_ids"]) <= {e.id for e in findings}
    assert scenarios[0]["missing_evidence"]
    assert all(e.score is None for e in findings)


def test_unrelated_assets_do_not_combine():
    assert not additional_scenarios(
        inspect_message("job offer", "a") + inspect_message("registration fee", "b")
    )


def test_email_headers_and_attachment_are_untrusted():
    from email.message import EmailMessage

    message = EmailMessage()
    message["From"] = "Recruiter <person@company.example>"
    message["Reply-To"] = "pay@unrelated.example"
    message["Subject"] = "Offer"
    message["Authentication-Results"] = "claimed.example; spf=pass"
    message.set_content("Job offer with a registration fee")
    message.add_attachment(
        b"harmless content",
        maintype="application",
        subtype="octet-stream",
        filename="../../offer.txt",
    )
    headers, body, attachments = parse_email(message.as_bytes())
    assert attachments == [("offer.txt", b"harmless content")]
    assert "registration fee" in body
    assert "not independently verified" in headers["authentication_limit"]
    assert any(e.label == "reply_to_mismatch" for e in email_findings(headers, "a"))

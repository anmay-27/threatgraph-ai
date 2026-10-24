"""Bounded text indicators. These describe content, not verified criminal intent."""

import re
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from app.schemas.evidence import finding

TERMS = {
    "recruitment_language": (
        "job offer",
        "recruitment",
        "onboarding",
        "offer letter",
        "selected for",
        "hiring",
    ),
    "advance_fee_request": (
        "registration fee",
        "processing fee",
        "training fee",
        "pay before",
        "refundable deposit",
    ),
    "payment_language": (
        "send payment",
        "bank transfer",
        "wire transfer",
        "pay immediately",
        "upi://pay",
        "payment required",
    ),
    "urgency_language": (
        "act now",
        "immediately",
        "within 24 hours",
        "urgent",
        "account suspended",
        "final warning",
    ),
    "credential_request": (
        "send your password",
        "share your otp",
        "provide your otp",
        "verify your password",
        "enter your password",
    ),
    "invoice_language": ("invoice", "payment due", "billing statement"),
    "payment_change": (
        "new bank account",
        "updated bank details",
        "changed bank details",
    ),
    "executive_claim": ("chief executive", "ceo", "managing director"),
}


def inspect_message(text, asset):
    text = text[:100000]
    evidence = [
        finding(
            asset,
            "message_parser",
            "metadata",
            "message_text",
            "Submitted or extracted text; statements in this content have not been independently verified.",
            metadata={"text": text[:20000]},
        )
    ]
    for label, terms in TERMS.items():
        matches = [
            term
            for term in terms
            if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I)
        ]
        if matches:
            evidence.append(
                finding(
                    asset,
                    "message_rules",
                    "social_engineering",
                    label,
                    "Content contains "
                    + label.replace("_", " ")
                    + ". This signal alone does not establish fraud.",
                    metadata={"phrases": matches},
                )
            )
    return evidence


def parse_email(data):
    message = BytesParser(policy=policy.default).parsebytes(data)
    headers = {
        key: str(message.get(key, ""))[:2000]
        for key in ("From", "Reply-To", "Return-Path", "Subject", "Date")
    }
    headers["Received"] = [str(x)[:2000] for x in message.get_all("Received", [])[:20]]
    headers["Authentication-Results"] = [
        str(x)[:2000] for x in message.get_all("Authentication-Results", [])[:10]
    ]
    headers["authentication_limit"] = (
        "Headers are sender-supplied evidence, not independently verified SPF, DKIM or DMARC results."
    )
    parts = []
    attachments = []
    total = 0
    for i, part in enumerate(message.walk()):
        if i >= 100:
            break
        if part.is_multipart():
            continue
        payload = part.get_payload(decode=True) or b""
        total += len(payload)
        if total > 25 * 1024 * 1024:
            raise ValueError("Decoded email exceeds investigation size budget")
        if part.get_filename() or part.get_content_disposition() == "attachment":
            if len(attachments) >= 10:
                raise ValueError("Email attachment limit exceeded")
            name = (
                (part.get_filename() or "attachment")
                .replace("\\", "/")
                .split("/")[-1][:200]
            )
            attachments.append((name, payload))
        elif part.get_content_type() in ("text/plain", "text/html"):
            try:
                content = payload.decode(
                    part.get_content_charset() or "utf-8", errors="replace"
                )
            except LookupError:
                content = payload.decode("utf-8", errors="replace")
            if part.get_content_type() == "text/html":
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(content[:200000], "html.parser")
                content = (
                    soup.get_text(" ", strip=True)
                    + " "
                    + " ".join(a["href"] for a in soup.select("a[href]")[:50])
                )
            parts.append(content[:50000])
    return headers, "\n".join(parts)[:100000], attachments


def email_findings(headers, asset):
    sender = parseaddr(headers["From"])[1]
    reply = parseaddr(headers["Reply-To"])[1]
    results = [
        finding(
            asset,
            "email_parser",
            "metadata",
            "email_headers",
            "Parsed email headers; authentication claims are unverified.",
            metadata={**headers, "sender": sender, "reply_to": reply},
        )
    ]
    if (
        sender
        and reply
        and sender.rsplit("@", 1)[-1].lower() != reply.rsplit("@", 1)[-1].lower()
    ):
        results.append(
            finding(
                asset,
                "email_parser",
                "identity_mismatch",
                "reply_to_mismatch",
                "Replies go to a different domain from the sender address. Mailing services may legitimately do this.",
                0.35,
                0.65,
                metadata={"sender": sender, "reply_to": reply},
            )
        )
    return results

from uuid import uuid4

# Required groups must all have supporting evidence on the same asset.
RULES = [
    (
        "recruitment_scam",
        "Potential recruitment / payment scam",
        ({"recruitment_language"}, {"advance_fee_request"}),
        "A recruitment message requests an advance fee. Verify the employer and payment request independently.",
        "Employer identity and legitimacy of the requested fee",
        [
            "Do not pay before independently verifying the offer.",
            "Contact the employer using its official website.",
        ],
    ),
    (
        "payment_scam",
        "Potential invoice payment diversion",
        ({"invoice_language"}, {"payment_change"}),
        "Invoice instructions refer to a changed payment destination. This requires independent verification.",
        "Previous verified payment details",
        ["Confirm payment changes through a previously verified contact."],
    ),
    (
        "social_engineering",
        "Potential credential social engineering",
        ({"credential_request"}, {"urgency_language"}),
        "The message combines a credential request with pressure to act quickly.",
        "Sender identity",
        [
            "Do not share passwords or one-time codes.",
            "Open the official service independently.",
        ],
    ),
    (
        "brand_impersonation",
        "Potential brand impersonation",
        ({"brand_domain_mismatch"}, {"credential_destination_mismatch"}),
        "Brand references and an off-domain credential destination appear together.",
        "Authorization of the third-party service",
        ["Visit the official organization website manually."],
    ),
    (
        "account_takeover",
        "Potential account takeover attempt",
        ({"credential_request"}, {"reply_to_mismatch"}),
        "A credential request accompanies mismatched email reply routing.",
        "Sender authorization",
        [
            "Do not reply with credentials.",
            "If credentials were shared, change them through the official service and enable MFA.",
        ],
    ),
]


def additional_scenarios(evidence):
    by_asset = {}
    for e in evidence:
        by_asset.setdefault(e.asset_id, []).append(e)
    result = []
    for asset, items in by_asset.items():
        labels = {e.label for e in items}
        for key, name, groups, why, missing, actions in RULES:
            if all(labels & group for group in groups):
                support = [
                    e.id for e in items if any(e.label in group for group in groups)
                ]
                result.append(
                    {
                        "id": str(uuid4()),
                        "label": name,
                        "scenario_name": key,
                        "asset_id": asset,
                        "evidence_ids": support,
                        "supporting_evidence": support,
                        "missing_evidence": [missing],
                        "confidence": 0.65,
                        "confidence_method": "Conservative rule strength; not a calibrated probability of fraud.",
                        "severity": "high" if key == "recruitment_scam" else "moderate",
                        "explanation": why,
                        "recommendations": actions,
                    }
                )
    return result

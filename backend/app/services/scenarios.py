from uuid import uuid4
from hashlib import sha256


def chain_scenarios(evidence, graph):
    """Join clues only along an observed directed delivery path, not by co-occurrence."""
    adjacency = {}
    for edge in graph.edges:
        if edge['relation'] in {'contains', 'links_to', 'resolves_to', 'downloads', 'redirects_to'}:
            adjacency.setdefault(edge['source'], []).append(edge['target'])
    result = []
    starts = [e for e in evidence if e.label == 'recruitment_language']
    fees = [e for e in evidence if e.label == 'advance_fee_request']
    for start in starts:
        for fee in fees:
            if start.asset_id == fee.asset_id:
                continue  # Covered by the existing same-asset rule.
            queue = [(start.asset_id, [start.asset_id])]
            visited = set()
            path = None
            while queue and len(visited) <= 500:
                node, route = queue.pop(0)
                if node == fee.asset_id:
                    path = route;break
                if node in visited:continue
                visited.add(node)
                queue.extend((child, route+[child]) for child in adjacency.get(node, []) if child not in visited)
            if path:
                support = [start.id, fee.id]
                result.append(dict(id='chain:'+sha256('|'.join(support).encode()).hexdigest()[:20], label='Potential recruitment / payment scam chain', scenario_name='recruitment_payment_chain', asset_id=start.asset_id, asset_path=path, evidence_ids=support, supporting_evidence=support, missing_evidence=['Independent verification of employer identity, fee purpose and payment recipient'], confidence=.65, confidence_method='Rule strength, not a probability of fraud', severity='high', explanation='Recruitment language leads through an observed attachment or URL path to an advance-fee request. This is a review hypothesis, not proof of criminal intent.', recommendations=['Pause payment and verify the offer through a separately obtained employer contact.', 'Verify the recipient and fee policy before sharing identity documents or money.']))
    return result[:50]

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

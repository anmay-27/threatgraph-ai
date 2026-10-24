from uuid import uuid4


class ThreatGraph:
    def __init__(self, limit=160):
        self.nodes = []
        self.edges = []
        self.limit = limit

    def node(self, kind, label, **data):
        if len(self.nodes) >= self.limit:
            return None
        identifier = str(uuid4())
        self.nodes.append(
            {"id": identifier, "type": kind, "label": label[:240], **data}
        )
        return identifier

    def edge(self, source, target, relation):
        if source and target:
            self.edges.append(
                {
                    "id": str(uuid4()),
                    "source": source,
                    "target": target,
                    "relation": relation,
                }
            )

    def export(self):
        return {"nodes": self.nodes, "edges": self.edges}


def infer_scenarios(evidence, graph):
    by_asset = {}
    for e in evidence:
        by_asset.setdefault(e.asset_id, []).append(e)
    scenarios = []
    qr_present = any(n["type"] == "qr_code" for n in graph.nodes)
    for asset, items in by_asset.items():
        labels = {e.label for e in items}
        if "credential_destination_mismatch" in labels and (
            "brand_domain_mismatch" in labels or "urgency_language" in labels
        ):
            scenarios.append(
                {
                    "id": str(uuid4()),
                    "label": "Potential credential phishing",
                    "explanation": "Pattern consistent with credential theft: a password form posts off-domain alongside impersonation or urgency indicators.",
                    "asset_id": asset,
                    "evidence_ids": [
                        e.id
                        for e in items
                        if e.category
                        in ("phishing", "identity_mismatch", "social_engineering")
                    ],
                }
            )

            # Require an actual directed path from a QR node to this asset.
            def reachable(start):
                todo, seen = [start], set()
                while todo:
                    node = todo.pop()
                    if node == asset:
                        return True
                    if node not in seen:
                        seen.add(node)
                        todo.extend(
                            e["target"] for e in graph.edges if e["source"] == node
                        )
                return False

            if qr_present and any(
                reachable(n["id"]) for n in graph.nodes if n["type"] == "qr_code"
            ):
                scenarios.append(
                    {
                        "id": str(uuid4()),
                        "label": "Potential QR phishing",
                        "explanation": "A decoded QR URL leads to credential-phishing indicators.",
                        "asset_id": asset,
                        "evidence_ids": [e.id for e in items],
                    }
                )
        if "executable" in labels and "signature_match" in labels:
            scenarios.append(
                {
                    "id": str(uuid4()),
                    "label": "Potential malware delivery",
                    "explanation": "Executable content matched an antivirus signature.",
                    "asset_id": asset,
                    "evidence_ids": [e.id for e in items],
                }
            )
    from app.services.scenarios import additional_scenarios
    scenarios.extend(additional_scenarios(evidence))
    for scenario in scenarios:
        scenario.setdefault('scenario_name',scenario['label'].lower().replace(' ','_'))
        scenario.setdefault('supporting_evidence',scenario['evidence_ids'])
        scenario.setdefault('missing_evidence',['Independent verification of operator identity and intent'])
        scenario.setdefault('confidence',0.65)
        scenario.setdefault('confidence_method','Conservative rule strength; not a calibrated fraud probability.')
        scenario.setdefault('severity','high')
        scenario.setdefault('recommendations',['Verify through an independently obtained official channel.'])
    return scenarios

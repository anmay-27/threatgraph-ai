import asyncio
import logging
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from sqlalchemy import delete
from app.core.config import settings
from app.core.fetch import fetch, normalize_url
from app.models.database import Analysis, ENTITIES, Session, ModelVersion
from app.schemas.evidence import finding
from app.analyzers.file.inspect import detect_mime, inspect_file
from app.analyzers.url.page import inspect_page
from app.analyzers.url.reputation import reputation
from app.analyzers.url.brands import lexical_findings
from app.analyzers.image.inspect import inspect_image, decode_qr
from app.analyzers.audio.inspect import inspect_audio
from app.analyzers.video.inspect import inspect_video
from app.services.registry import predict_url, registry
from app.fusion.engine import conflicts, fuse
from app.threat_graph.graph import ThreatGraph, infer_scenarios
from app.services.coverage import investigation_checks
from app.services.intelligence import index_analysis
from app.services.intelligence import extract_text
from app.analyzers.message import inspect_message, parse_email, email_findings
from app.services.jobs import checkpoint, InvestigationCancelled
from app.models.cases import now

log = logging.getLogger(__name__)


def progress(identifier, message, state="PROCESSING"):
    with Session() as db:
        row = db.get(Analysis, identifier)
        checkpoint(db, identifier)
        row.state = state
        row.progress = [
            *row.progress,
            {"step": message, "state": "completed", "timestamp": now().isoformat()},
        ]
        db.commit()


class Investigation:
    def __init__(self, identifier):
        self.id = identifier
        self.graph = ThreatGraph(settings.max_nodes * 5)
        self.evidence = []
        self.assets = []
        self.visited = {}
        self.bytes = 0
        self.partial = False
        self.temp = tempfile.TemporaryDirectory(prefix="threatgraph-")

    def issue(self, asset, source, message):
        self.partial = True
        self.evidence.append(finding(asset, source, "metadata", "unavailable", message))

    async def text(self, text, node, depth=0):
        self.evidence.extend(inspect_message(text, node))
        for kind, value in extract_text(text):
            if kind == "URL":
                await self.url(value, node, "links_to", depth + 1)
            else:
                self.graph.edge(node, self.graph.node(kind.lower(), value), "mentions")

    async def url(self, value, parent=None, relation="links_to", depth=0):
        with Session() as db:
            checkpoint(db, self.id)
            db.commit()
        if depth > settings.max_depth or len(self.assets) >= settings.max_nodes:
            self.issue(
                parent or self.id,
                "recursion",
                "Traversal limit reached; remaining assets were not fetched.",
            )
            return
        try:
            url = normalize_url(value)
        except ValueError as exc:
            node = self.graph.node("url", value)
            self.graph.edge(parent, node, relation)
            self.issue(node, "safe_fetch", str(exc))
            return
        if url in self.visited:
            self.graph.edge(parent, self.visited[url], relation)
            return
        node = self.graph.node("url", url)
        self.graph.edge(parent, node, relation)
        self.visited[url] = node
        self.assets.append({"id": node, "type": "url", "url": url})
        structure = lexical_findings(url, node)
        self.evidence.extend(structure)
        listed_first_party = bool(structure[0].metadata.get("listed_first_party_domains"))
        domain_node = self.graph.node("domain", urlsplit(url).hostname)
        self.graph.edge(node, domain_node, "hosted_on")
        try:
            nested_resource = relation in {"contains", "downloads"}
            if not nested_resource and not listed_first_party:
                self.evidence.append(predict_url(url, node))
            else:
                reason = "The experimental URL-pattern model was not applied to a locally listed first-party domain; this does not certify safety." if listed_first_party else "The experimental URL-pattern model was not applied to a nested resource; it assesses the submitted URL only."
                self.evidence.append(finding(node, "url_detector", "metadata", "url_model_skipped", reason, metadata={"listed_first_party": listed_first_party, "nested_resource": nested_resource}))
            self.evidence.extend(reputation(url, node))
        except Exception as exc:
            self.issue(
                node, "url_detector", f"URL inference failed: {type(exc).__name__}"
            )
        try:
            if self.bytes >= 25 * 1024 * 1024:
                raise ValueError("Investigation download budget exhausted")
            response = await fetch(
                url, min(10 * 1024 * 1024, 25 * 1024 * 1024 - self.bytes)
            )
            self.bytes += len(response.body)
            if response.network:
                self.evidence.append(
                    finding(
                        node,
                        "safe_fetch",
                        "metadata",
                        "network_metadata",
                        "Network observations from the protected fetch; HTTPS is not a safety verdict.",
                        metadata=response.network,
                    )
                )
            current = node
            for _, target in response.redirects:
                redirected = self.visited.get(target) or self.graph.node("url", target)
                self.visited[target] = redirected
                self.graph.edge(current, redirected, "redirects_to")
                current = redirected
            if response.redirects:
                self.evidence.append(
                    finding(
                        node,
                        "safe_fetch",
                        "redirect",
                        "redirect_chain",
                        "Redirects were validated before fetching.",
                        metadata={"chain": response.redirects},
                    )
                )
            path = Path(self.temp.name) / str(uuid4())
            path.write_bytes(response.body)
            await self.file(
                path, response.url, parent=current, depth=depth, url=response.url,
                embedded_resource=depth > 0 and relation == "contains",
            )
            progress(self.id, f"Fetched and inspected {urlsplit(url).hostname}")
        except InvestigationCancelled:
            raise
        except Exception as exc:
            detail = str(exc)
            if "Access is denied" in detail or "Permission denied" in detail:
                detail = "Outbound network access was denied by the runtime; page content and redirects could not be inspected. URL structure alone cannot establish safety or phishing."
            self.issue(node, "safe_fetch", f"Fetch did not complete: {detail[:220]}")

    async def qr(self, values, parent, depth):
        from app.analyzers.qr import classify_qr

        for value in values[:10]:
            decoded = classify_qr(value)
            safe_value = (
                "WiFi QR (credentials withheld)" if decoded["type"] == "WIFI" else value
            )
            node = self.graph.node("qr_code", safe_value)
            self.graph.edge(parent, node, "contains")
            self.evidence.append(
                finding(
                    parent,
                    "qr_decoder",
                    "qr_code",
                    "qr_decoded",
                    "QR payload decoded; a QR code alone is not suspicious.",
                    metadata={"payload": safe_value[:2000], **decoded},
                )
            )
            if decoded.get("payment_identifier"):
                self.graph.edge(
                    node,
                    self.graph.node("upi_id", decoded["payment_identifier"]),
                    "resolves_to",
                )
            if value.lower().startswith(("http://", "https://")):
                await self.url(value, node, "resolves_to", depth + 1)

    async def file(self, path, name, parent=None, depth=0, url=None, embedded_resource=False):
        with Session() as db:
            checkpoint(db, self.id)
            db.commit()
        if len(self.assets) >= settings.max_nodes:
            self.issue(parent, "recursion", "Asset count limit reached.")
            return
        mime = detect_mime(path.read_bytes()[:8192])
        kind = (
            mime.split("/")[0]
            if mime.startswith(("image/", "audio/", "video/")) and mime != "image/svg+xml"
            else "webpage"
            if mime == "text/html"
            else "file"
        )
        node = self.graph.node(kind, name)
        self.graph.edge(parent, node, "contains")
        metadata, evidence = inspect_file(path, name, node)
        if embedded_resource:
            for item in evidence:
                if item.label == "extension_mismatch":
                    item.metadata["risk_eligible"] = False
                    item.explanation += " This was an embedded page resource, so the mismatch does not raise the submitted URL's security score."
        self.assets.append({"id": node, "type": kind, "name": name, **metadata})
        self.evidence.extend(evidence)
        try:
            urls = []
            if name.lower().endswith(".eml"):
                if depth >= settings.max_depth:
                    self.issue(
                        node, "email_parser", "Nested email depth limit reached."
                    )
                    return
                headers, body, attachments = parse_email(path.read_bytes())
                self.evidence.extend(email_findings(headers, node))
                await self.text(headers["Subject"] + "\n" + body, node, depth)
                for attachment_name, data in attachments:
                    target = Path(self.temp.name) / str(uuid4())
                    target.write_bytes(data)
                    await self.file(
                        target, attachment_name, parent=node, depth=depth + 1
                    )
            elif mime == "image/svg+xml":
                # Kept as file evidence; raster image models cannot decode SVG.
                # XML namespace references do not represent outbound navigation.
                pass
            elif kind == "image":
                image_metadata, found, urls = inspect_image(path, node)
                self.evidence.extend(found)
                if image_metadata.get("ocr"):
                    await self.text(image_metadata["ocr"], node, depth)
            elif kind == "audio":
                _, found = inspect_audio(path, node)
                self.evidence.extend(found)
            elif kind == "video":
                _, found, urls = inspect_video(path, node)
                self.evidence.extend(found)
            elif kind == "webpage":
                page, found, assets = inspect_page(
                    path.read_bytes(), url or "https://uploaded.invalid/", node
                )
                self.evidence.extend(found)
                self.evidence.append(
                    finding(
                        node,
                        "webpage",
                        "metadata",
                        "page_metadata",
                        "Static HTML inspection; scripts were not executed.",
                        metadata=page,
                    )
                )
                if url and depth == 0 and settings.enable_browser_inspection:
                    try:
                        from app.analyzers.url.browser import inspect_browser
                        observation = await inspect_browser(path.read_bytes(), url, settings.browser_channel)
                        rendered, rendered_findings, _ = inspect_page(observation.pop('html'), url, node)
                        existing = {(e.label, str(e.metadata)) for e in self.evidence if e.asset_id == node}
                        for item in rendered_findings:
                            if item.label != 'collection_surface' and (item.label, str(item.metadata)) not in existing:
                                item.metadata['observed_in'] = 'restricted_browser'
                                self.evidence.append(item)
                        self.evidence.append(finding(node,'browser_inspector','metadata','browser_observation','Observed initial page rendering through restricted public-resource fetching.',metadata={**observation,'rendered_collection':rendered['data_collection']}))
                    except Exception as exc:
                        self.issue(node,'browser_inspector',f'Browser inspection did not complete ({type(exc).__name__}). Static page findings remain available.')
                for brand in page["brands"]:
                    self.graph.edge(
                        node, self.graph.node("brand", brand), "claims_brand"
                    )
                if page["password_fields"]:
                    form = self.graph.node("credential_form", "Password form")
                    self.graph.edge(node, form, "contains")
                    for target in page["form_destinations"][:5]:
                        self.graph.edge(
                            form, self.graph.node("url", target), "submits_to"
                        )
                # Uploaded HTML never causes outbound requests to embedded assets.
                if url:
                    for link, relation in assets:
                        await self.url(link, node, relation, depth + 1)
            elif mime == "application/pdf" or "officedocument" in mime or "macroEnabled" in mime:
                from app.analyzers.file.document import inspect_document
                text, found, document_links = inspect_document(path, mime, node)
                self.evidence.extend(found)
                if text.strip():
                    self.evidence.extend(inspect_message(text, node))
                urls.extend(value for item in found if item.label == 'document_summary' for value in item.metadata.get('qr_values', []))
                # Declared hyperlinks are recorded; never fetched just by uploading a document.
            elif mime.startswith("text/") or name.lower().endswith(".txt"):
                await self.text(
                    path.read_bytes()[:100000].decode("utf-8", errors="replace"),
                    node,
                    depth,
                )
            await self.qr(urls, node, depth)
            progress(self.id, f"Inspected {kind}: {Path(name).name[:80]}")
        except InvestigationCancelled:
            raise
        except Exception as exc:
            log.warning("Analyzer failed: %s", type(exc).__name__)
            self.issue(
                node,
                kind + "_analyzer",
                f"Analysis did not complete: {type(exc).__name__}: {str(exc)[:160]}",
            )

    def report(self):
        from app.services.scenarios import additional_scenarios

        for scenario in additional_scenarios(self.evidence):
            self.evidence.append(
                finding(
                    scenario["asset_id"],
                    "fraud_rules",
                    "social_engineering",
                    scenario["scenario_name"],
                    scenario["explanation"],
                    0.65,
                    0.65,
                    metadata={
                        "supporting_evidence": scenario["evidence_ids"],
                        "missing_evidence": scenario["missing_evidence"],
                        "score_method": "Rule-based prioritization, not a calibrated probability of fraud.",
                    },
                )
            )
        self.partial |= any(
            e.label in ("unavailable", "verification_unavailable")
            for e in self.evidence
        )
        disagreements = conflicts(self.evidence)
        result = fuse(self.evidence, disagreements, self.partial)
        for e in self.evidence:
            node = self.graph.node(
                "detector_finding",
                e.label.replace("_", " "),
                severity=e.severity,
                evidence_id=e.id,
            )
            self.graph.edge(e.asset_id, node, "flagged_by")
        mapping = {
            n.get("evidence_id"): n["id"]
            for n in self.graph.nodes
            if n.get("evidence_id")
        }
        for c in disagreements:
            self.graph.edge(
                mapping.get(c["evidence_a"]),
                mapping.get(c["evidence_b"]),
                "conflicts_with",
            )
        scenarios = infer_scenarios(self.evidence, self.graph)
        result["recommendations"] = list(
            dict.fromkeys(
                [action for s in scenarios for action in s.get("recommendations", [])]
                + result["recommendations"]
            )
        )
        explanations = [
            {
                "evidence_id": e.id,
                "finding": e.label.replace("_", " "),
                "why": e.explanation,
                "confidence": e.confidence,
                "limitations": "This detector finding is not proof of intent or authenticity. Review coverage, metadata and model limitations.",
                "recommendation": result["recommendations"][0],
            }
            for e in self.evidence
        ]
        return {
            **result,
            "evidence": [e.model_dump() for e in self.evidence],
            "explanations": explanations,
            "checks": investigation_checks(self.assets, self.evidence),
            "conflicts": disagreements,
            "graph": self.graph.export(),
            "assets": self.assets,
            "scenarios": scenarios,
            "categories": sorted(
                {
                    e.category
                    for e in self.evidence
                    if e.score is not None and e.score >= 0.5
                }
            ),
            "provenance": [e.model_dump() for e in self.evidence if e.source == "c2pa"],
            "model_results": [
                e.model_dump() for e in self.evidence if e.source.endswith("_detector")
            ],
            "explanation": scenarios[0]["explanation"]
            if scenarios
            else "Review the individual findings. Limited coverage or contradictory evidence requires independent verification.",
        }


def run(identifier: str):
    investigation = Investigation(identifier)
    try:
        progress(identifier, "Investigation started")
        with Session() as db:
            row = db.get(Analysis, identifier)
        if row.input_type == "url":
            asyncio.run(investigation.url(row.name))
        else:
            asyncio.run(investigation.file(Path(row.path), row.name))
        progress(identifier, "Evidence conflicts and risk fusion completed")
        report = investigation.report()
        with Session() as db:
            row = db.get(Analysis, identifier)
            checkpoint(db, identifier)
            row.report = report
            if row.input_type == "url":
                fetched = next((a for a in report["assets"] if a.get("sha256")), None)
                if fetched:
                    row.sha256 = fetched["sha256"]
                    row.mime = fetched["mime"]
                    row.size = fetched["size"]
            row.state = "PARTIAL" if investigation.partial else "COMPLETED"
            index_analysis(db, row)
            payloads = {
                "assets": report["assets"],
                "evidence": report["evidence"],
                "detector_results": report["model_results"],
                "evidence_conflicts": report["conflicts"],
                "graph_nodes": report["graph"]["nodes"],
                "graph_edges": report["graph"]["edges"],
                "fraud_scenarios": report["scenarios"],
            }
            for name, items in payloads.items():
                table = ENTITIES[name]
                db.execute(delete(table).where(table.analysis_id == identifier))
                for item in items:
                    db.add(
                        table(
                            id=f"{identifier}:{uuid4()}",
                            analysis_id=identifier,
                            payload=item,
                        )
                    )
            for model in registry():
                if model["available"]:
                    db.merge(
                        ModelVersion(
                            id=f"{model['name']}:{model['version']}", payload=model
                        )
                    )
            db.commit()
    except InvestigationCancelled:
        with Session() as db:
            row = db.get(Analysis, identifier)
            row.state = "CANCELLED"
            row.error = "Cancelled at a safe pipeline boundary. Start a new analysis or retry to obtain a complete report."
            row.report = None
            db.commit()
    except Exception as exc:
        log.exception("Investigation failed")
        with Session() as db:
            row = db.get(Analysis, identifier)
            row.state = "FAILED"
            row.error = f"{type(exc).__name__}: {str(exc)[:200]}"
            db.commit()
    finally:
        investigation.temp.cleanup()

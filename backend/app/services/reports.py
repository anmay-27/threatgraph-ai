"""Offline PDF rendering with no HTML, remote fonts, or network resources."""

from pathlib import Path
import fitz
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.models.database import Session, Analysis, serialize
from app.services.cases import case_detail
from app.services.intelligence import analysis_entities
from app.services.auth import accessible
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["reports"])
FONT_CANDIDATES = (
    Path(__file__).resolve().parents[1] / 'assets/fonts/DejaVuSans.ttf',
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)
REPORT_FONT = next((path for path in FONT_CANDIDATES if path.is_file()), None)
REPORT_BOLD = Path(__file__).resolve().parents[1] / 'assets/fonts/DejaVuSans-Bold.ttf'


def wrap_pdf_text(value, font, size, width=505):
    """Wrap using actual glyph widths, including long URLs and Unicode text."""
    output=[]
    for paragraph in str(value).splitlines() or ['']:
        current=''
        for word in paragraph.split():
            candidate=(current+' '+word).strip()
            if font.text_length(candidate,fontsize=size)<=width:
                current=candidate;continue
            if current:output.append(current);current=''
            while font.text_length(word,fontsize=size)>width:
                low,high=1,len(word)
                while low<high:
                    middle=(low+high+1)//2
                    if font.text_length(word[:middle],fontsize=size)<=width:low=middle
                    else:high=middle-1
                output.append(word[:low]);word=word[low:]
            current=word
        output.append(current)
    return output


def render_pdf(title, identifier, analyses, entities=(), timeline=(), feedback_by_analysis=None):
    doc = fitz.open()
    page = None
    y = 0
    measured_font = fitz.Font(fontfile=str(REPORT_FONT)) if REPORT_FONT else fitz.Font('helv')
    measured_bold = fitz.Font(fontfile=str(REPORT_BOLD)) if REPORT_BOLD.is_file() else measured_font

    def line(text, size=10):
        nonlocal page, y
        value = str(text)
        if not REPORT_FONT:
            value = value.encode("latin-1", "replace").decode("latin-1")
        font = measured_bold if size >= 12 and REPORT_BOLD.is_file() else measured_font
        for chunk in wrap_pdf_text(value, font, size):
            if page is None or y + size + 6 > 770:
                page = doc.new_page(width=595, height=842)
                y = 55
                page.draw_rect(fitz.Rect(0, 0, 595, 9), color=(.23, .46, .84), fill=(.23, .46, .84))
                if REPORT_FONT:
                    page.insert_font(fontname="reportfont", fontfile=str(REPORT_FONT))
                if REPORT_BOLD.is_file():
                    page.insert_font(fontname='reportbold',fontfile=str(REPORT_BOLD))
                page.insert_text(
                    (45, 28),
                    "ThreatGraph AI | Digital Trust & Fraud Investigation",
                    fontsize=9,
                    color=(0.2, 0.3, 0.5),
                )
                page.draw_line((45, 38), (550, 38), color=(.8, .84, .9))
            page.insert_text((45, y), chunk, fontsize=size, fontname='reportbold' if size >= 12 and REPORT_BOLD.is_file() else "reportfont" if REPORT_FONT else ("hebo" if size >= 12 else "helv"), color=(.09, .14, .22))
            y += size + 6

    def heading(value):
        nonlocal y
        if y > 690:
            y = 771  # Keep a section heading with at least its first paragraph.
        y += 9
        line(value, 14)
        y += 3

    def summary_panel(row, report):
        nonlocal y
        if page is None or y > 665:
            line("Assessment at a glance", 12)
        top = y + 2
        page.draw_rect(fitz.Rect(45, top, 550, top + 76), color=(.78, .85, .94), fill=(.94, .97, 1))
        font = "reportfont" if REPORT_FONT else "helv"
        model = next((e for e in report.get("evidence", []) if e.get("source") == "image_detector" and isinstance(e.get("score"), (int, float))), None)
        labels = [
            ("SECURITY RISK", str(report.get("risk_level") or "UNKNOWN")),
            ("EVIDENCE COVERAGE", "NOT RECORDED" if not report.get("checks") else "PARTIAL" if any(c.get("status") in {"partial", "unavailable", "not_checked"} for c in report["checks"]) else "CHECKED"),
            ("IMAGE ORIGIN", "UNVERIFIED" if row.get("input_type") == "image" else "NOT APPLICABLE"),
        ]
        for i, (label, value) in enumerate(labels):
            x = 59 + i * 169
            page.insert_text((x, top + 24), label, fontsize=8, fontname=font, color=(.2, .34, .54))
            page.insert_text((x, top + 48), value, fontsize=12, fontname=font, color=(.08, .14, .23))
        y = top + 88
        if model:
            line("Image model suggestion: {} at {:.1f}% AI-pattern score. This is not a verified origin verdict.".format(str((model.get("metadata") or {}).get("verdict", "unknown")).replace("_", " "), model["score"] * 100))

    def image_context(report):
        evidence = report.get("evidence", [])
        model = next((e for e in evidence if e.get("source") == "image_detector" and isinstance(e.get("score"), (int, float))), None)
        if not model:
            heading("Image origin: insufficient model evidence")
            line("No image-model prediction was available. Missing metadata does not establish camera origin or AI generation.")
            return
        meta = model.get("metadata") or {}
        heading("Image origin: what was actually observed")
        line("AI-pattern model score: {:.1f}% | Saved suggestion: {}".format(model["score"] * 100, str(meta.get("verdict", "unknown")).replace("_", " ")))
        line("This number is a screening score calibrated on a limited research dataset. It is not the real-world probability that this particular image was AI-made.")
        if meta.get("verdict") == "likely_real":
            line("A non-AI suggestion can be a FALSE NEGATIVE. Convincing AI portraits, new generators, editing and resizing may evade the learned patterns.")
        elif meta.get("verdict") == "likely_ai_generated":
            line("An AI suggestion is not proof of origin. Obtain source history or signed provenance before making a consequential claim.")
        else:
            line("The classifier could not give a dependable class suggestion. Treat origin as unresolved.")
        if meta.get("ood") == "not_estimated":
            line("The system did not check whether this image is outside the model's familiar training domain.")
        if meta.get("stability_checks"):
            line("Same-model sensitivity checks, not independent votes:")
            for check in meta["stability_checks"][:5]:
                if isinstance(check.get("score"), (int, float)):
                    line("- {}: {:.1f}%".format(check.get("name", "view"), check["score"] * 100))
        heading("What the model cannot explain")
        line("This whole-image classifier cannot locate altered pixels, diagnose faces or hands, or identify the generating tool. No specific visual defect was established by this analysis. A fully AI-made image may have no obvious flaw.")
        heading("How to verify and improve the assessment")
        line("1. Obtain the original file and creation/editing history. Forwarded files and screenshots can strip useful origin evidence.")
        line("2. Check signed Content Credentials if available, and compare the file with its original publisher or creator.")
        line("3. For an identity or document claim, verify directly with the person or issuing organization; this model cannot authenticate either.")
        line("4. If the true origin is known, record this result as a model error. Evaluate that generator and editing workflow on a separate labeled set before changing thresholds or claiming better accuracy.")

    def image_preview(row):
        nonlocal page, y
        raw = row.get("path")
        if not raw:
            return False
        try:
            source = Path(raw).resolve()
            if not source.is_relative_to(settings.storage_dir.resolve()) or source.stat().st_size > 25 * 1024 * 1024:
                return False
            preview = doc.new_page(width=595, height=842)
            preview.draw_rect(fitz.Rect(0, 0, 595, 9), color=(.23, .46, .84), fill=(.23, .46, .84))
            preview.insert_text((45, 34), "THREATGRAPH AI  |  SUBMITTED IMAGE", fontsize=10, color=(.2, .3, .5))
            preview.insert_image(fitz.Rect(50, 70, 545, 700), filename=str(source), keep_proportion=True)
            preview.insert_text((45, 738), "Original submitted file; appearance alone does not establish origin.", fontsize=9)
            page = None
            y = 0
            return True
        except (OSError, RuntimeError, ValueError):
            # Retention may have removed the original. The report still exports.
            return False

    line(title, 18)
    line(("Analysis ID: " if title == "Investigation report" else "Case ID: ") + identifier)
    heading("Executive Summary")
    line(
        "This report records observed indicators and limitations, not a safety certificate or confirmation of criminal intent."
    )
    for row in analyses:
        r = row.get("report") or {}
        heading(row["name"])
        line("Analysis: " + row["id"] + " | " + str(row.get("created_at", "")))
        summary_panel(row, r)
        line("Evidence confidence: {} | Uncertainty: {} | Analysis state: {}".format('not estimated' if r.get('risk_score') is None else r.get("confidence", "unknown"), r.get("uncertainty", "unknown"), row["state"]))
        line(r.get("explanation", "No completed report"))
        if row.get('input_type') == 'image':
            line("Security risk is separate from AI image origin. A low AI score cannot prove that a file is genuine.")
        if row.get("input_type") == "image":
            image_context(r)
            if not image_preview(row):
                line("Original image preview unavailable for this export. The stored evidence and model result remain; the original upload may have expired under the retention policy.")
        if row.get('input_type') == 'url':
            from app.services.url_summary import summarize_url
            summary = summarize_url(row['name'], r)
            heading(summary['title'])
            line(summary['meaning'])
            for observation in summary['observations']: line('- ' + observation)
            heading('Findings and why they matter')
            if not summary['findings']: line('No high-risk indicator was identified by the completed checks. Missing checks are not negative results.')
            for item in summary['findings']: line(item['label'].replace('_',' ') + ': ' + item['explanation'])
            heading('What you should do next')
            for action in summary['actions']: line('- ' + action)
            heading('Unresolved checks')
            for gap in summary['gaps']: line('- ' + gap)
        feedback = (feedback_by_analysis or {}).get(row["id"], [])
        for item in r.get('evidence', []):
            if item.get('label') != 'document_summary': continue
            heading('Document investigation')
            line(item['explanation'])
            meta = item.get('metadata', {})
            heading('Extracted text preview')
            line(meta.get('text_preview') or 'No readable text extracted; scanned content may need OCR.')
            for link in meta.get('links', []): line('Declared link (not opened): ' + link)
            for gap in meta.get('limitations', []): line('Coverage gap: ' + gap)
            line('Next steps: verify the sender and document claims; review active-content findings and malware scan coverage before enabling macros or opening embedded objects.')
        if feedback:
            heading("Investigator feedback - not model output")
            line("Reviewer statement, not independently verified by ThreatGraph. Feedback does not change the saved detector score or retrain the model.")
            for item in feedback:
                line("{} | Finding {} | {}".format(item["verdict"].upper(), item["evidence_id"], item["note"] or "No note provided"))
        for s in r.get("scenarios", []):
            line(s["label"] + ": " + s["explanation"])
            line("Missing evidence: " + ", ".join(s.get("missing_evidence", [])))
        heading("Recommended actions")
        for action in r.get("recommendations", []):
            line("- " + action)
        heading("Checks completed and gaps")
        checks = r.get("checks") or []
        if not checks:
            line("No check-by-check coverage information was saved with this report.")
        for check in checks:
            line("{} - {}. {}".format(check.get("title", check.get("id", "Check")), check.get("status", "unknown"), check.get("summary", "")))
            for reason in check.get("unavailable_reasons") or []:
                line("Unavailable because: " + reason)
            if check.get("status") in {"partial", "unavailable", "not_checked"} and check.get("limitations"):
                line("Limit: " + check["limitations"])
        heading("Evidence considered")
        for e in r.get("evidence", []):
            line(
                str(e.get("label", "finding"))
                + " | "
                + str(e.get("severity", "info"))
                + " | "
                + str(e.get("source", "unknown"))
                + " | "
                + e.get("model_version", "")
            )
            line(e.get("explanation", "No explanation recorded"))
            line("Evidence ID: " + e.get("id", "unknown"))
        heading("Technical appendix")
        line("SHA-256: " + str(row.get("sha256") or "Not applicable"))
        line("Model and rule outputs above are preserved as recorded. Export JSON for the complete metadata and graph payload.")
        heading("Evidence graph relationships")
        graph = r.get("graph", {})
        labels = {n["id"]: n["label"] for n in graph.get("nodes", [])}
        # Vector graph overview. The complete edge list below retains omitted detail.
        visible = graph.get("nodes", [])[:24]
        if visible:
            page = doc.new_page(width=595, height=842)
            y = 55
            if REPORT_FONT:
                page.insert_font(fontname="reportfont", fontfile=str(REPORT_FONT))
            if REPORT_BOLD.is_file():
                page.insert_font(fontname='reportbold',fontfile=str(REPORT_BOLD))
            page.insert_text(
                (45, 28),
                "ThreatGraph AI | Evidence graph overview (first 24 nodes)",
                fontsize=10,
            )
            positions = {
                n["id"]: (70 + (i % 3) * 175, 80 + (i // 3) * 80)
                for i, n in enumerate(visible)
            }
            for edge in graph.get("edges", []):
                if edge["source"] in positions and edge["target"] in positions:
                    a = positions[edge["source"]]
                    b = positions[edge["target"]]
                    page.draw_line(
                        fitz.Point(a[0] + 45, a[1] + 15),
                        fitz.Point(b[0] + 45, b[1] + 15),
                        color=(0.6, 0.65, 0.7),
                        width=0.7,
                    )
            for n in visible:
                x, cy = positions[n["id"]]
                page.draw_rect(
                    fitz.Rect(x - 15, cy - 8, x + 125, cy + 42),
                    color=(0.2, 0.3, 0.5),
                    fill=(0.93, 0.96, 1),
                )
                label = (
                    (n["type"] + ": " + n["label"])
                    .encode("latin-1", "replace")
                    .decode("latin-1")
                )
                page.insert_textbox(
                    fitz.Rect(x - 10, cy - 3, x + 120, cy + 40), label[:65], fontsize=8,
                    fontname="reportfont" if REPORT_FONT else "helv",
                )
            y = 760
            line("Graph overview is bounded. Full directed relations follow.", 9)
        for edge in graph.get("edges", []):
            line(
                labels.get(edge["source"], edge["source"])
                + " -> "
                + edge["relation"]
                + " -> "
                + labels.get(edge["target"], edge["target"])
            )
    heading("Entities")
    for e in entities:
        line(e["type"] + ": " + e["display_value"])
    heading("Case timeline")
    for e in timeline:
        line(str(e["created_at"]) + " | " + e["action"] + " | " + e["content"])
    heading("Limitations")
    line(
        "AI-generated does not mean malicious. No malware detected does not mean safe. Missing provenance does not prove fabrication. Model benchmarks are not guarantees of field accuracy. The graph overview is bounded; complete directed relations are listed. JSON preserves complete metadata."
    )
    data = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return data


@router.get("/analyses/{identifier}/report.pdf")
def analysis_pdf(identifier: str):
    from app.services.feedback import Feedback
    from sqlalchemy import select

    with Session() as db:
        row = db.get(Analysis, identifier)
        if not row or not accessible(db, identifier):
            raise HTTPException(404, "Analysis not found")
        if not row.report:
            raise HTTPException(409, "Report is not ready")
        feedback = [{"verdict": f.verdict, "evidence_id": f.evidence_id, "note": f.note}
                    for f in db.scalars(select(Feedback).where(Feedback.analysis_id == identifier)
                                        .order_by(Feedback.created_at.desc()).limit(50))]
        data = render_pdf(
            "Investigation report",
            identifier,
            [{**serialize(row), "path": row.path}],
            analysis_entities(identifier),
            feedback_by_analysis={identifier: feedback},
        )
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="threatgraph-{identifier}-investigation.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/cases/{identifier}/report.pdf")
def case_pdf(identifier: str):
    from app.services.feedback import Feedback
    from sqlalchemy import select

    case = case_detail(identifier)
    entities = {
        e["id"]: e for a in case["analyses"] for e in analysis_entities(a["id"])
    }
    ids = [a["id"] for a in case["analyses"]]
    feedback = {i: [] for i in ids}
    if ids:
        with Session() as db:
            originals = {a.id: a.path for a in db.query(Analysis).filter(Analysis.id.in_(ids)).all()}
            for f in db.scalars(select(Feedback).where(Feedback.analysis_id.in_(ids)).order_by(Feedback.created_at.desc())):
                if len(feedback[f.analysis_id]) < 50:
                    feedback[f.analysis_id].append({"verdict": f.verdict, "evidence_id": f.evidence_id, "note": f.note})
        for analysis in case["analyses"]:
            analysis["path"] = originals.get(analysis["id"])
    data = render_pdf(
        case["title"],
        identifier,
        case["analyses"],
        entities=entities.values(),
        timeline=case["timeline"],
        feedback_by_analysis=feedback,
    )
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="threatgraph-case-{identifier}-investigation.pdf"',
            "Cache-Control": "no-store",
        },
    )

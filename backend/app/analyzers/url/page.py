from urllib.parse import urljoin
from bs4 import BeautifulSoup
from app.analyzers.url.features import domain
from app.schemas.evidence import finding
from app.analyzers.url.privacy import inspect_collection

from app.analyzers.url.brands import BRANDS


def inspect_page(html: bytes, url: str, asset: str):
    soup = BeautifulSoup(html[:2_000_000], "html.parser")
    text = soup.get_text(" ", strip=True)[:50000]
    forms = soup.find_all("form")
    passwords = soup.select('input[type="password"]')
    mismatches = [
        urljoin(url, f.get("action", url))
        for f in forms
        if domain(urljoin(url, f.get("action", url))) != domain(url)
    ]
    evidence = []
    if passwords:
        evidence.append(
            finding(
                asset,
                "webpage",
                "phishing",
                "password_form",
                "Page requests a password. This is an observation, not a phishing indicator by itself; inspect the submission destination and site identity.",
            )
        )
    collection, collection_evidence = inspect_collection(soup, url, asset)
    evidence.extend(collection_evidence)
    brands = [
        b
        for b, official in BRANDS.items()
        if b in text.lower() and domain(url) not in official
    ]
    if brands:
        evidence.append(
            finding(
                asset,
                "webpage",
                "identity_mismatch",
                "brand_domain_mismatch",
                "Page mentions a brand outside its listed official domains. Third-party references may be legitimate.",
                0.65 if passwords else 0.3,
                0.65,
                metadata={"brands": brands},
            )
        )
    urgency = [
        p
        for p in (
            "verify immediately",
            "account suspended",
            "urgent payment",
            "act now",
            "within 24 hours",
        )
        if p in text.lower()
    ]
    if urgency:
        evidence.append(
            finding(
                asset,
                "webpage",
                "social_engineering",
                "urgency_language",
                "Urgent language can pressure visitors into acting without verification.",
                0.45,
                0.65,
                metadata={"phrases": urgency},
            )
        )
    payment = [
        p
        for p in ("wire transfer", "send payment", "bank transfer", "pay immediately")
        if p in text.lower()
    ]
    if payment:
        evidence.append(
            finding(
                asset,
                "webpage",
                "social_engineering",
                "payment_language",
                "Payment instructions were found; payment language alone does not establish fraud.",
                0.3,
                0.6,
                metadata={"phrases": payment},
            )
        )
    metadata = {
        "title": soup.title.get_text()[:200] if soup.title else "",
        "text": text[:3000],
        "forms": len(forms),
        "password_fields": len(passwords),
        "iframes": len(soup.find_all("iframe")),
        "scripts": len(soup.find_all("script")),
        "brands": brands,
        "form_destinations": mismatches,
        "data_collection": collection,
        "links": [urljoin(url, a["href"]) for a in soup.select("a[href]")[:30]],
        "favicon": [
            urljoin(url, a["href"]) for a in soup.select('link[rel~="icon"][href]')[:1]
        ],
    }
    assets = [(urljoin(url, a["src"]), "contains") for a in soup.select("img[src]")[:6]]
    assets += [
        (urljoin(url, a["href"]), "downloads")
        for a in soup.select("a[download][href]")[:3]
    ]
    return metadata, evidence, assets

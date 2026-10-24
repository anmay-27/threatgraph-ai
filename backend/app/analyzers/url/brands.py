"""Small transparent brand reference; mentions alone never establish impersonation."""

from urllib.parse import urlsplit
import ipaddress
from app.schemas.evidence import finding

BRANDS = {
    "microsoft": {"microsoft.com", "live.com", "office.com", "microsoftonline.com"},
    "google": {"google.com"},
    "amazon": {"amazon.com", "amazon.in"},
    "paypal": {"paypal.com"},
    "apple": {"apple.com", "icloud.com"},
    "sbi": {"sbi.co.in", "onlinesbi.sbi"},
    "hdfc": {"hdfcbank.com"},
    "icici": {"icicibank.com"},
}


def distance(a, b):
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (x != y))
            )
        previous = current
    return previous[-1]


def lexical_findings(url, asset):
    host = (urlsplit(url).hostname or "").lower()
    labels = host.split(".")
    signals = {
        "punycode": any(x.startswith("xn--") for x in labels),
        "subdomain_labels": max(0, len(labels) - 2),
        "https": urlsplit(url).scheme == "https",
    }
    try:
        ipaddress.ip_address(host)
        signals["ip_as_host"] = True
    except ValueError:
        signals["ip_as_host"] = False
    lookalikes = []
    official_matches = []
    for brand, official in BRANDS.items():
        matched = sorted(d for d in official if host == d or host.endswith("." + d))
        if matched:
            official_matches.append({"brand": brand, "base_domain": matched[0]})
            continue
        for token in host.replace("-", ".").split("."):
            if len(brand) >= 5 and 0 < distance(token, brand) <= 1:
                lookalikes.append(
                    {
                        "brand": brand,
                        "token": token,
                        "edit_distance": distance(token, brand),
                    }
                )
    signals["lookalikes"] = lookalikes
    signals["listed_first_party_domains"] = official_matches
    return [
        finding(
            asset,
            "url_structure",
            "metadata",
            "url_structure",
            "URL structure and spelling similarities are screening clues, not confirmation of impersonation.",
            metadata=signals,
        )
    ]

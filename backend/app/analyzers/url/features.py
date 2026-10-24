import ipaddress
import math
import re
from collections import Counter
from urllib.parse import urlsplit
import tldextract

extract_domain = tldextract.TLDExtract(suffix_list_urls=())
FEATURE_NAMES = [
    "length",
    "host_length",
    "dots",
    "subdomains",
    "digits",
    "special",
    "hyphens",
    "at",
    "encoded",
    "depth",
    "query_length",
    "suspicious_tld",
    "ip_host",
    "punycode",
    "entropy",
    "repeated",
    "https",
]


def domain(url: str) -> str:
    result = extract_domain(url)
    return result.top_domain_under_public_suffix or (
        urlsplit(url if "://" in url else "//" + url).hostname or result.domain
    )


def features(url: str) -> list[float]:
    u = urlsplit(url)
    host = u.hostname or ""
    try:
        ipaddress.ip_address(host)
        ip = 1
    except ValueError:
        ip = 0
    counts = Counter(url)
    entropy = (
        -sum(n / len(url) * math.log2(n / len(url)) for n in counts.values())
        if url
        else 0
    )
    return [
        len(url),
        len(host),
        host.count("."),
        max(0, len(extract_domain(host).subdomain.split(".")))
        if extract_domain(host).subdomain
        else 0,
        sum(c.isdigit() for c in url),
        sum(not c.isalnum() for c in url),
        url.count("-"),
        int("@" in url),
        url.count("%"),
        len([p for p in u.path.split("/") if p]),
        len(u.query),
        int(host.rsplit(".", 1)[-1] in {"zip", "top", "click", "xyz", "work"}),
        ip,
        int("xn--" in host),
        entropy,
        max([len(x.group()) for x in re.finditer(r"(.)\1+", url)] or [0]),
        int(u.scheme == "https"),
    ]

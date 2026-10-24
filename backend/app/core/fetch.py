"""Bounded HTTP fetch with validated, pinned DNS answers on every redirect."""

import asyncio
import ipaddress
import socket
import zlib
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit, urlunsplit
import aiohttp
from aiohttp.abc import AbstractResolver


class UnsafeURL(ValueError):
    pass


class BoundedBody:
    """Bound both transferred and expanded bytes, including gzip responses."""
    def __init__(self, encoding, limit):
        self.limit=limit;self.transferred=0;self.body=bytearray()
        encoding=encoding.strip().lower()
        if encoding not in {'identity','gzip','deflate'}:raise UnsafeURL('Unsupported HTTP content encoding')
        self.decoder=zlib.decompressobj(31 if encoding=='gzip' else 15) if encoding!='identity' else None

    def feed(self, block):
        self.transferred+=len(block)
        if self.transferred>self.limit:raise UnsafeURL('Response exceeds download limit')
        data=self.decoder.decompress(block,self.limit-len(self.body)+1) if self.decoder else block
        self.body.extend(data)
        if len(self.body)>self.limit:raise UnsafeURL('Expanded response exceeds download limit')

    def finish(self):
        if self.decoder and (not self.decoder.eof or self.decoder.unused_data):
            raise UnsafeURL('Incomplete or trailing compressed response')
        return bytes(self.body)


def normalize_url(value: str) -> str:
    if len(value) > 8192 or any(ord(c) < 33 for c in value) or "\\" in value:
        raise UnsafeURL("Invalid URL characters or length")
    try:
        u = urlsplit(value)
        if (
            u.scheme.lower() not in ("http", "https")
            or not u.hostname
            or u.username
            or u.password
        ):
            raise UnsafeURL("Only HTTP(S) URLs without credentials are supported")
        host = u.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        port = u.port
        if port not in (None, 80, 443):
            raise UnsafeURL("Only ports 80 and 443 are supported")
        if (
            host == "localhost"
            or "." not in host
            and ":" not in host
            or host.endswith((".local", ".internal", ".localhost"))
        ):
            raise UnsafeURL("Internal hostnames are prohibited")
        try:
            validate_ip(host)
        except ValueError as exc:
            if isinstance(exc, UnsafeURL):
                raise
        authority = f"[{host}]" if ":" in host else host
        if port:
            authority += f":{port}"
        return urlunsplit((u.scheme.lower(), authority, u.path or "/", u.query, ""))
    except (UnicodeError, ValueError) as exc:
        raise UnsafeURL(str(exc)) from exc


def validate_ip(value: str):
    address = ipaddress.ip_address(value)
    if (
        not address.is_global
        or address.is_multicast
        or address.is_reserved
        or getattr(address, "ipv4_mapped", None)
        or getattr(address, "sixtofour", None)
        or getattr(address, "teredo", None)
    ):
        raise UnsafeURL("Non-public network destination blocked")
    return address


class PublicResolver(AbstractResolver):
    def __init__(self):
        self.observed = []

    async def resolve(self, host, port=0, family=socket.AF_INET):
        answers = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=family, type=socket.SOCK_STREAM
        )
        # Reject mixed public/private answers, not just the selected address.
        for answer in answers:
            validate_ip(answer[4][0])
        self.observed.append(
            {"host": host, "addresses": sorted({a[4][0] for a in answers})}
        )
        return [
            dict(
                hostname=host,
                host=a[4][0],
                port=port,
                family=a[0],
                proto=a[2],
                flags=socket.AI_NUMERICHOST,
            )
            for a in answers
        ]

    async def close(self):
        pass


@dataclass
class FetchResult:
    url: str
    body: bytes
    mime: str
    redirects: list[tuple[str, str]]
    status: int
    network: dict = field(default_factory=dict)


async def fetch(url: str, max_bytes: int = 10 * 1024 * 1024) -> FetchResult:
    current = normalize_url(url)
    redirects = []
    resolver = PublicResolver()
    connector = aiohttp.TCPConnector(resolver=resolver, use_dns_cache=False, limit=4)
    # trust_env=False prevents proxy environment variables bypassing DNS controls.
    async with asyncio.timeout(35):
        async with aiohttp.ClientSession(
            connector=connector,
            trust_env=False,
            auto_decompress=False,
            timeout=aiohttp.ClientTimeout(total=15, connect=5),
            headers={
                "User-Agent": "ThreatGraphAI/1.0 DefensiveResearch",
                "Accept-Encoding": "identity",
            },
        ) as client:
            for _ in range(6):
                async with client.get(current, allow_redirects=False) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        target = normalize_url(
                            urljoin(current, response.headers.get("Location", ""))
                        )
                        if target == current or any(a == target for a, _ in redirects):
                            raise UnsafeURL("Redirect loop")
                        redirects.append((current, target))
                        current = target
                        continue
                    response.raise_for_status()
                    if response.content_length and response.content_length > max_bytes:
                        raise UnsafeURL("Response exceeds download limit")
                    body = BoundedBody(response.headers.get('Content-Encoding','identity'), max_bytes)
                    connection = getattr(response, "connection", None)
                    transport = getattr(connection, "transport", None)
                    ssl_object = (
                        transport.get_extra_info("ssl_object") if transport else None
                    )
                    certificate = ssl_object.getpeercert() if ssl_object else None
                    async for block in response.content.iter_chunked(65536):
                        body.feed(block)
                    return FetchResult(
                        current,
                        body.finish(),
                        response.content_type,
                        redirects,
                        response.status,
                        {
                            "dns": resolver.observed,
                            "https": current.startswith("https://"),
                            "certificate": certificate,
                            "limitation": "Transport encryption and domain certificate validation do not establish operator identity or site safety.",
                        },
                    )
    raise UnsafeURL("Redirect limit exceeded")

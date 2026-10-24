import asyncio
import socket
import pytest
from app.core.fetch import normalize_url, PublicResolver, UnsafeURL
from app.analyzers.file.inspect import detect_mime


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com",
        "http://localhost",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://169.254.169.254",
        "http://[::1]",
        "http://[::ffff:127.0.0.1]",
        "http://192.168.1.1",
        "https://example.com:8000",
        "http://user:pass@example.com",
        "http://host.internal",
        "https://example.com\\@127.0.0.1",
        "http://0.0.0.0",
        "http://[2001:db8::1]",
    ],
)
def test_ssrf(url):
    with pytest.raises(UnsafeURL):
        normalize_url(url)


def test_normalize():
    assert normalize_url("HTTPS://Example.COM/a#fragment") == "https://example.com/a"
    assert normalize_url("https://bücher.de") == "https://xn--bcher-kva.de/"


def test_dns_mixed_answers(monkeypatch):
    async def check():
        async def answers(*a, **k):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 443)),
            ]

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", answers)
        with pytest.raises(UnsafeURL):
            await PublicResolver().resolve("example.com", 443)

    asyncio.run(check())


def test_mime_ignores_filename():
    assert detect_mime(b"%PDF-1.7\n") == "application/pdf"
    assert detect_mime(b"<!doctype html><html>hello</html>") == "text/html"
    assert detect_mime(b"\x00\x01\x00") == "application/octet-stream"

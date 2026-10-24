import asyncio
import pytest
from app.core.fetch import fetch, UnsafeURL


def test_redirect_to_private_is_blocked_before_second_request(monkeypatch):
    seen = []

    class Response:
        status = 302
        headers = {"Location": "http://169.254.169.254/latest/meta-data"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class Client:
        def __init__(self, **kwargs):
            self.connector = kwargs["connector"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.connector.close()

        def get(self, url, **kwargs):
            seen.append(url)
            return Response()

    monkeypatch.setattr("app.core.fetch.aiohttp.ClientSession", Client)
    with pytest.raises(UnsafeURL):
        asyncio.run(fetch("https://example.com/"))
    assert seen == ["https://example.com/"]


def test_redirect_loop_is_bounded(monkeypatch):
    seen = []

    class Response:
        status = 302
        headers = {"Location": "https://example.com/"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class Client:
        def __init__(self, **kwargs):
            self.connector = kwargs["connector"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.connector.close()

        def get(self, url, **kwargs):
            seen.append(url)
            return Response()

    monkeypatch.setattr("app.core.fetch.aiohttp.ClientSession", Client)
    with pytest.raises(UnsafeURL, match="loop"):
        asyncio.run(fetch("https://example.com/"))
    assert len(seen) == 1

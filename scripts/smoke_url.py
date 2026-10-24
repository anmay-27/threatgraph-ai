"""Read-only real network smoke test against example.com, never a feed URL."""

import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / "backend"), str(root)]
from app.core.fetch import fetch
from app.services.registry import predict_url


async def main():
    result = await fetch("https://example.com/")
    assert result.status == 200 and b"Example Domain" in result.body
    model = predict_url(result.url, "smoke")
    assert model.score is not None
    print(
        {
            "url": result.url,
            "status": result.status,
            "bytes": len(result.body),
            "phishing_probability": model.score,
            "model_version": model.model_version,
        }
    )


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import cv2
from app.analyzers.image.inspect import decode_qr
from app.core.fetch import FetchResult
from app.models.database import Analysis, Base, Session, engine
from app.services.investigation import Investigation


def test_qr_decoder():
    image = cv2.QRCodeEncoder_create().encode("https://example.com/")
    image = cv2.copyMakeBorder(image, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    image = cv2.resize(image, (420, 420), interpolation=cv2.INTER_NEAREST)
    assert decode_qr(image) == ["https://example.com/"]


def test_recursive_qr_path(monkeypatch):
    Base.metadata.create_all(engine)
    with Session() as db:
        row = Analysis(name="QR chain", input_type="url")
        db.add(row)
        db.commit()
        identifier = row.id
    seen = []

    async def mock_fetch(url, *args):
        seen.append(url)
        if url == "https://entry.example/":
            return FetchResult(
                url,
                b'<html><img src="https://image.example/qr.png"></html>',
                "text/html",
                [],
                200,
            )
        if url == "https://image.example/qr.png":
            qr = cv2.QRCodeEncoder_create().encode("https://login.example/")
            qr = cv2.copyMakeBorder(qr, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
            qr = cv2.resize(qr, (400, 400), interpolation=cv2.INTER_NEAREST)
            return FetchResult(
                url, cv2.imencode(".png", qr)[1].tobytes(), "image/png", [], 200
            )
        return FetchResult(
            url,
            b'<html>Microsoft verify immediately<form action="https://collector.example/"><input type="password"></form></html>',
            "text/html",
            [],
            200,
        )

    monkeypatch.setattr("app.services.investigation.fetch", mock_fetch)
    case = Investigation(identifier)
    try:
        asyncio.run(case.url("https://entry.example/"))
        asyncio.run(case.url("https://entry.example/"))
        report = case.report()
        assert len(seen) == 3
        assert any(e["relation"] == "resolves_to" for e in report["graph"]["edges"])
        assert any(s["label"] == "Potential QR phishing" for s in report["scenarios"])
    finally:
        case.temp.cleanup()

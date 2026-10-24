import io
import shutil
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ExifTags, ImageChops, ImageStat
from app.schemas.evidence import finding
from app.services.registry import predict_media
from app.analyzers.provenance.inspect import inspect_provenance
from app.analyzers.image.generation import generation_markers

Image.MAX_IMAGE_PIXELS = 25_000_000


def decode_qr(image: np.ndarray) -> list[str]:
    scanner = cv2.QRCodeDetector()
    success, decoded, _, _ = scanner.detectAndDecodeMulti(image)
    if success:
        return list(dict.fromkeys(x for x in decoded if x))[:10]
    value, _, _ = scanner.detectAndDecode(image)
    return [value] if value else []


def inspect_image(path: Path, asset: str):
    with Image.open(path) as original:
        original.load()
        exif = {
            ExifTags.TAGS.get(k, str(k)): str(v)[:300]
            for k, v in original.getexif().items()
        }
        encoding = original.format
        markers = generation_markers(original.info, exif)
        image = original.convert("RGB")
    gray = cv2.cvtColor(np.asarray(image.resize((32, 32))), cv2.COLOR_RGB2GRAY)
    dct = cv2.dct(gray.astype(np.float32))[:8, :8]
    phash = hex(
        int("".join("1" if x else "0" for x in (dct > np.median(dct)).flatten()), 2)
    )[2:].zfill(16)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    recompressed = Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")
    ela = sum(ImageStat.Stat(ImageChops.difference(image, recompressed)).mean) / 3
    metadata = {
        "width": image.width,
        "height": image.height,
        "encoding": encoding,
        "exif": exif,
        "perceptual_hash": phash,
        "recompression_mean_error": ela,
        "generation_markers": markers,
    }
    evidence = [
        finding(
            asset,
            "image_forensics",
            "metadata",
            "image_metadata",
            "EXIF absence and recompression error do not prove manipulation. Error level is descriptive only.",
            metadata=metadata,
        )
    ]
    if markers:
        evidence.append(finding(asset, "image_forensics", "metadata", "generation_metadata", "Embedded metadata describes an AI-generation workflow. Metadata is editable and may refer to only part of an image; it is not verified provenance.", metadata={"markers": markers, "verified": False}))
    evidence.extend(inspect_provenance(path, asset))
    evidence.append(predict_media(path, "image", asset))
    thumb = image.copy()
    thumb.thumbnail((1800, 1800))
    urls = decode_qr(cv2.cvtColor(np.asarray(thumb), cv2.COLOR_RGB2BGR))
    if shutil.which("tesseract"):
        try:
            import pytesseract

            metadata["ocr"] = pytesseract.image_to_string(thumb, timeout=10)[:5000]
        except Exception:
            evidence.append(
                finding(
                    asset, "ocr", "metadata", "unavailable", "OCR did not complete."
                )
            )
    else:
        evidence.append(
            finding(
                asset, "ocr", "metadata", "unavailable", "Tesseract is not installed."
            )
        )
    evidence[0].metadata.update(metadata)
    return metadata, evidence, urls

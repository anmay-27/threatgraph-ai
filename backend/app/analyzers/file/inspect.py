import hashlib
import io
import mimetypes
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
import filetype
from app.schemas.evidence import finding
from app.core.config import settings


def detect_mime(data: bytes) -> str:
    if data.startswith(b'PK'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
                for marker, subtype in [('word/document.xml','wordprocessingml.document'),('xl/workbook.xml','spreadsheetml.sheet'),('ppt/presentation.xml','presentationml.presentation')]:
                    if '[Content_Types].xml' in names and marker in names:
                        return 'application/vnd.openxmlformats-officedocument.' + subtype
        except zipfile.BadZipFile:
            pass
    kind = filetype.guess(data)
    if kind:
        return kind.mime
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    start = data[:4096].lstrip().lower()
    # SVG is XML, not prose. Do not treat its namespace URLs as links to crawl.
    xml_start = re.sub(rb'^(?:(?:<\?xml[^>]*\?>|<!--.*?-->)\s*)*', b'', start, flags=re.S)
    if re.match(rb'<svg(?:\s|>)', xml_start):
        return "image/svg+xml"
    if start.startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
        return "text/html"
    try:
        text = data[:8192].decode("utf-8")
        if "\x00" not in text:
            return "text/plain"
    except UnicodeDecodeError:
        pass
    return "application/octet-stream"


def inspect_file(path: Path, name: str, asset: str):
    data = path.read_bytes()
    mime = detect_mime(data)
    metadata = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
        "mime": mime,
        "size": len(data),
    }
    evidence = [
        finding(
            asset,
            "file_inspector",
            "metadata",
            "file_metadata",
            "Hashes identify content; MD5 is provided only for compatibility.",
            metadata=metadata,
        )
    ]
    expected = mimetypes.guess_type(name)[0]
    aliases = {'video/avi':'video/x-msvideo', 'video/msvideo':'video/x-msvideo', 'audio/x-wav':'audio/wav', 'audio/wave':'audio/wav'}
    expected = aliases.get(expected, expected)
    if (
        expected
        and expected != aliases.get(mime, mime)
        and not (expected.startswith("text/") and mime.startswith("text/"))
    ):
        evidence.append(
            finding(
                asset,
                "file_inspector",
                "file_security",
                "extension_mismatch",
                f"Filename suggests {expected}; inspected bytes indicate {mime}.",
                0.4,
            )
        )
    if data.startswith((b"MZ", b"\x7fELF")):
        evidence.append(
            finding(
                asset,
                "file_inspector",
                "file_security",
                "executable",
                "Executable content detected. This does not independently establish malware.",
                0.55,
                0.9,
            )
        )
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            metadata["archive"] = [
                {"name": x.filename, "size": x.file_size, "compressed": x.compress_size}
                for x in entries[:200]
            ]
            if (
                len(entries) > 200
                or sum(x.file_size for x in entries) > 100 * 1024 * 1024
                or any(x.file_size / max(x.compress_size, 1) > 200 for x in entries)
            ):
                evidence.append(
                    finding(
                        asset,
                        "file_inspector",
                        "file_security",
                        "archive_limits",
                        "Archive expansion exceeds limits; no contents were extracted.",
                        0.6,
                        0.9,
                    )
                )
            if any(
                ".." in Path(x.filename).parts or x.filename.startswith(("/", "\\"))
                for x in entries
            ):
                evidence.append(
                    finding(
                        asset,
                        "file_inspector",
                        "file_security",
                        "archive_path_traversal",
                        "Archive contains unsafe member paths; no contents were extracted.",
                        0.8,
                        0.95,
                    )
                )
    evidence[0].metadata.update(metadata)
    if settings.clamav_host:
        from app.analyzers.file.antivirus import scan_daemon

        try:
            matched, detail = scan_daemon(path, settings.clamav_host)
            evidence.append(
                finding(
                    asset,
                    "clamav",
                    "malware",
                    "signature_match" if matched else "no_signature_match",
                    detail,
                    1.0 if matched else 0.05,
                    0.95 if matched else 0.5,
                )
            )
        except Exception:
            evidence.append(
                finding(
                    asset,
                    "clamav",
                    "file_security",
                    "unavailable",
                    "Local ClamAV daemon did not complete the scan.",
                )
            )
    elif shutil.which("clamscan"):
        try:
            result = subprocess.run(
                ["clamscan", "--no-summary", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, OSError):
            evidence.append(
                finding(
                    asset,
                    "clamav",
                    "file_security",
                    "unavailable",
                    "ClamAV scan exceeded its timeout or could not start.",
                )
            )
            return metadata, evidence
        if result.returncode in (0, 1):
            evidence.append(
                finding(
                    asset,
                    "clamav",
                    "malware",
                    "signature_match" if result.returncode else "no_signature_match",
                    "ClamAV: " + result.stdout[:1000],
                    1.0 if result.returncode else 0.05,
                    0.95 if result.returncode else 0.5,
                )
            )
        else:
            evidence.append(
                finding(
                    asset,
                    "clamav",
                    "file_security",
                    "unavailable",
                    "ClamAV scanner could not complete.",
                )
            )
    else:
        evidence.append(
            finding(
                asset,
                "clamav",
                "file_security",
                "unavailable",
                "ClamAV is not installed; no malware signature verdict is available.",
            )
        )
    return metadata, evidence

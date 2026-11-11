"""Local capability probes; readiness never promises a successful analysis."""
import importlib.util
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter
from app.services.registry import registry
from app.analyzers.file.antivirus import daemon_status
from app.core.config import settings

router = APIRouter(prefix='/api/v1', tags=['readiness'])

@router.get('/readiness')
def readiness():
    checks = []
    def add(name, ready, detail, action):
        checks.append(dict(name=name, status='ready' if ready else 'attention', detail=detail, action='' if ready else action))
    image = next((m for m in registry() if m['name'] == 'image'), {})
    add('Image model', image.get('available', False), image.get('version', 'No checkpoint registered') + '; installation check, not an accuracy guarantee', 'Install the registered image checkpoint and run the model smoke test.')
    scan = daemon_status(settings.clamav_host)
    add('Malware scanner', scan['available'], scan.get('version', scan.get('reason', 'Unavailable')), 'Start the local ClamAV service and retry.')
    fresh = False
    try:
        stamp = datetime.strptime(scan['version'].split('/')[-1].strip(), '%a %b %d %H:%M:%S %Y').replace(tzinfo=timezone.utc)
        fresh = 0 <= (datetime.now(timezone.utc)-stamp).days <= 7
    except (KeyError, ValueError): pass
    add('Malware signatures', fresh, 'Signature age within seven days' if fresh else 'Signatures are stale or their age could not be verified', 'Run the local signature updater before relying on malware screening.')
    for name, module in [('PDF extraction', 'fitz'), ('QR extraction', 'cv2'), ('Office documents', 'xml.etree.ElementTree')]:
        add(name, importlib.util.find_spec(module) is not None, 'Dependency availability check', 'Install the backend requirements and restart the API.')
    add('Scanned-document OCR', bool(shutil.which('tesseract')) and importlib.util.find_spec('pytesseract') is not None, 'Optional text recognition for scanned pages', 'Install Tesseract and make it available on PATH; text PDFs still work without OCR.')
    return dict(checked_at=datetime.now(timezone.utc).isoformat(), checks=checks, scope='Preflight checks do not submit files or access external websites. Per-investigation failures remain visible in results.')

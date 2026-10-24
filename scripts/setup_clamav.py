"""Install official portable ClamAV into this workspace (no system service)."""
import hashlib
import json
import zipfile
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.5.4'
TARGET=ROOT/'tools'/'clamav'

def main():
    TARGET.mkdir(parents=True,exist_ok=True)
    archive=TARGET/f'clamav-{VERSION}.zip'
    url=f'https://www.clamav.net/downloads/production/clamav-{VERSION}.win.x64.zip'
    if not archive.exists():
        with requests.get(url,stream=True,timeout=90) as response:
            response.raise_for_status()
            partial=archive.with_suffix('.partial')
            with partial.open('wb') as out:
                for block in response.iter_content(1024*1024):
                    out.write(block)
                    if out.tell()>350_000_000: raise ValueError('Package too large')
            partial.replace(archive)
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            if not (TARGET/item.filename).resolve().is_relative_to(TARGET.resolve()): raise ValueError('Unsafe archive path')
        package.extractall(TARGET)
    bin_dir=next(TARGET.rglob('clamd.exe')).parent
    database=TARGET/'database';database.mkdir(exist_ok=True)
    (TARGET/'freshclam.conf').write_text(f'DatabaseDirectory "{database}"\nDatabaseMirror database.clamav.net\nUpdateLogFile "{TARGET / "freshclam.log"}"\n',encoding='utf-8')
    (TARGET/'clamd.conf').write_text(f'DatabaseDirectory "{database}"\nTCPSocket 3310\nTCPAddr 127.0.0.1\nLogFile "{TARGET / "clamd.log"}"\nStreamMaxLength 260M\nMaxScanSize 300M\nMaxFileSize 260M\nMaxRecursion 10\n',encoding='utf-8')
    (TARGET/'install.json').write_text(json.dumps({'version':VERSION,'source':url,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bin_dir':str(bin_dir)},indent=2))
    print(str(bin_dir/'freshclam.exe'),flush=True)

if __name__=='__main__':main()

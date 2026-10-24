"""Fetch a pinned, safetensors-only VideoMAE research checkpoint; no remote code."""
import hashlib
import json
from pathlib import Path
import requests

REPO = 'SoraExplora/VideoMae'
REVISION = '8456c9f29444cda60484d5403513d1bc695fb1ad'
DEST = Path('models/video/videomae-ffpp')

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    response = requests.get(f'https://huggingface.co/api/models/{REPO}/tree/{REVISION}', timeout=60)
    response.raise_for_status()
    files = {f['path']: f for f in response.json()}
    audit = []
    for name in ['README.md', 'config.json', 'preprocessor_config.json', 'model.safetensors']:
        item = files[name]
        target = DEST / name
        expected = item.get('lfs', {}).get('oid')
        if not (target.exists() and expected and hashlib.sha256(target.read_bytes()).hexdigest() == expected):
            partial = target.with_suffix(target.suffix + '.part')
            offset = partial.stat().st_size if partial.exists() else 0
            with requests.get(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}', headers={'Range': f'bytes={offset}-'} if offset else {}, stream=True, timeout=(30,120)) as download:
                download.raise_for_status()
                if download.status_code == 206 and not download.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                    raise ValueError('Unexpected download range')
                with partial.open('ab' if offset and download.status_code == 206 else 'wb') as out:
                    for chunk in download.iter_content(1024*1024):
                        out.write(chunk)
            if partial.stat().st_size != item['size']:
                raise ValueError('Incomplete model download')
            if expected and hashlib.sha256(partial.read_bytes()).hexdigest() != expected:
                raise ValueError('Model checksum mismatch')
            partial.replace(target)
        audit.append({'file': name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size})
        print('Verified', name, flush=True)
    (DEST / 'source.json').write_text(json.dumps({'repository': REPO, 'revision': REVISION, 'license': 'MIT (mirror declaration)', 'provenance': 'Mirror attributes training to Vansh180/VideoMae-deepfake-detector; original repository was inaccessible. Publisher metrics are not independently verified.', 'files': audit}, indent=2))

if __name__ == '__main__':
    main()

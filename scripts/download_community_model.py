"""Download the official pinned Community Forensics weights; never execute remote code."""
import hashlib
import json
from pathlib import Path
import requests

REPO = 'OwensLab/commfor-model-384'
REVISION = '6076002bf0d9dd37537f965ee2f06f826c333b61'
CODE_REVISION = 'ee5b71d43db0f3779e1edd64ee927b13f2dd6ad4'
DEST = Path('models/image/community-forensics-384')

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    response = requests.get(f'https://huggingface.co/api/models/{REPO}/tree/{REVISION}', timeout=60)
    response.raise_for_status()
    files = {f['path']: f for f in response.json()}
    audit = []
    for name in ['README.md', 'config.json', 'model.safetensors']:
        item = files[name]
        target = DEST / name
        expected = item.get('lfs', {}).get('oid')
        if not (target.exists() and expected and hashlib.sha256(target.read_bytes()).hexdigest() == expected):
            temporary = target.with_suffix(target.suffix + '.part')
            offset = temporary.stat().st_size if temporary.exists() else 0
            with requests.get(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}', headers={'Range': f'bytes={offset}-'} if offset else {}, stream=True, timeout=(30,120)) as download:
                download.raise_for_status()
                if download.status_code == 206 and not download.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                    raise ValueError('Unexpected partial download range')
                with temporary.open('ab' if offset and download.status_code == 206 else 'wb') as out:
                    for chunk in download.iter_content(1024*1024):
                        out.write(chunk)
            if temporary.stat().st_size != item['size'] or (expected and hashlib.sha256(temporary.read_bytes()).hexdigest() != expected):
                raise ValueError('Model size/checksum mismatch')
            temporary.replace(target)
        audit.append(dict(file=name, sha256=hashlib.sha256(target.read_bytes()).hexdigest(), bytes=target.stat().st_size))
        print('Verified', name, flush=True)
    (DEST / 'source.json').write_text(json.dumps(dict(repository=REPO, revision=REVISION, code_revision=CODE_REVISION, license='MIT', files=audit), indent=2))

if __name__ == '__main__':
    main()

"""Install pinned, hash-verified research weights during the image build."""
import hashlib
import json
import shutil
import argparse
from pathlib import Path
import requests


def download(url, path, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256()
    with requests.get(url, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()
        with path.open('wb') as output:
            for block in response.iter_content(1024 * 1024):
                checksum.update(block)
                output.write(block)
    if expected and checksum.hexdigest() != expected:
        path.unlink()
        raise ValueError('Checkpoint checksum mismatch')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modalities', nargs='+', choices=('image', 'video'), default=['image', 'video'])
    args = parser.parse_args()
    for modality in args.modalities:
        source = Path('docker/model-manifests') / (modality + '.json')
        record = json.loads(source.read_text())
        root = Path('models') / modality
        folder = (root / record['file_path']).parent
        repo, revision = record['source']['repository'], record['source']['revision']
        files = record['source'].get('files') or [
            {'file': 'model.onnx', 'sha256': record['sha256']},
            {'file': 'README.md'},
        ]
        for item in files:
            name = item['file']
            download(f'https://huggingface.co/{repo}/resolve/{revision}/{name}', folder / name, item.get('sha256'))
        shutil.copy2(source, root / 'registry.json')
        print('Installed pinned', modality, 'research model')


if __name__ == '__main__':
    main()

"""Create a source-only release; never include user investigations or model binaries."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('backend', 'frontend', 'ml', 'scripts', 'docker', 'browser-extension')
FILES = ('README.md', '.gitignore', '.dockerignore', '.env.example', 'docker-compose.yml', 'pytest.ini')
EXCLUDED = {'node_modules', 'dist', '__pycache__', '.pytest_cache', '.ruff_cache', 'test-results', 'playwright-report'}
SUFFIXES = {'.pyc', '.db', '.log', '.pem', '.key', '.p12', '.pfx', '.pt', '.safetensors', '.joblib'}


def source_files():
    for name in FILES:
        if (ROOT / name).is_file():
            yield ROOT / name
    for directory in DIRECTORIES:
        for path in (ROOT / directory).rglob('*'):
            relative = path.relative_to(ROOT)
            if (path.is_file() and not path.is_symlink()
                    and not any(part in EXCLUDED for part in relative.parts)
                    and path.suffix.lower() not in SUFFIXES
                    and not path.name.startswith('.env')):
                yield path
    # Documentation text only: screenshots can contain submitted private content.
    yield from (ROOT / 'docs').glob('*.md')
    yield ROOT / 'models/README.md'
    yield from (ROOT / 'datasets/scripts').glob('*.py')


def main():
    output = ROOT / 'release'
    output.mkdir(exist_ok=True)
    entries = []
    with zipfile.ZipFile(output / 'threatgraph-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(source_files())):
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(relative, data)
            entries.append({'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (output / 'manifest.json').write_text(json.dumps(entries, indent=2))
    print(json.dumps({'files': len(entries), 'bytes': (output / 'threatgraph-source.zip').stat().st_size,
                      'archive': 'release/threatgraph-source.zip', 'deployed': False}))


if __name__ == '__main__':
    main()

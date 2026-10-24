"""Deterministic, conservative duplicate-filtered research subset (not full GenImage)."""
import csv
import argparse
import hashlib
import io
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.fft import dctn
import pyarrow.parquet as pq
from PIL import Image, ImageOps

GENERATORS = ['Real', 'ADM', 'BigGAN', 'GLIDE', 'Midjourney', 'SD14', 'SD15', 'VQDM', 'Wukong']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-dir', type=Path, default=Path('datasets/raw/tiny-genimage'))
    parser.add_argument('--output-dir', type=Path, default=Path('datasets/prepared/tiny-genimage-v1'))
    parser.add_argument('--train-per-class', type=int, default=400)
    parser.add_argument('--eval-per-class', type=int, default=100)
    parser.add_argument('--test-per-class', type=int, default=200)
    parser.add_argument('--exclude-manifest', type=Path, nargs='+')
    args = parser.parse_args()
    source, output = args.raw_dir, args.output_dir
    if (output / 'manifest.csv').exists():
        raise RuntimeError('Prepared dataset exists; retain immutable experiment inputs.')
    output.mkdir(parents=True, exist_ok=True)
    candidates, rejected = [], Counter()
    names, pixels, phashes = set(), set(), []
    for excluded in args.exclude_manifest or []:
        for row in csv.DictReader(excluded.open(encoding='utf-8-sig')):
            names.add(row['group'])
            pixels.add(row['pixel_hash'])
            phashes.append(int(row['phash'], 16))
    # Dedupe across both source partitions before assigning experiment splits.
    for split in ['train', 'validation']:
        for index, row in enumerate(row for shard in sorted(source.glob(split + '*.parquet')) for row in pq.read_table(shard).to_pylist()):
            blob = row['image']['bytes']
            generator = GENERATORS[row['generator']]
            identity = generator + ':' + Path(row['image']['path']).name.lower()
            with Image.open(io.BytesIO(blob)) as original:
                image = ImageOps.exif_transpose(original).convert('RGB')
                digest = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
                coefficients = dctn(np.asarray(image.convert('L').resize((32, 32)), dtype=float))[:8, :8]
                phash = int(''.join('1' if bit else '0' for bit in (coefficients > np.median(coefficients)).flat), 2)
            reason = 'source_identity' if identity in names else 'decoded_pixels' if digest in pixels else 'near_duplicate' if any((phash ^ old).bit_count() <= 4 for old in phashes) else None
            if reason:
                rejected[reason] += 1
                continue
            names.add(identity)
            pixels.add(digest)
            phashes.append(phash)
            candidates.append(dict(source_split=split, index=index, blob=blob, label=row['label'], generator=generator, group=identity, pixel_hash=digest, phash=f'{phash:016x}', source_file=row['image']['path']))
    rng = random.Random(42)
    pools = defaultdict(list)
    for row in candidates:
        pools[(row['source_split'], row['generator'])].append(row)
    for pool in pools.values():
        rng.shuffle(pool)
    def take(source_split, count, synthetic, heldout=False):
        gens = ['Midjourney'] if heldout else [g for g in GENERATORS[1:] if g != 'Midjourney'] if synthetic else ['Real']
        selected = []
        while len(selected) < count:
            active = [g for g in gens if pools[(source_split, g)]]
            if not active:
                raise ValueError(f'Insufficient data: {source_split}, {gens}, {count}')
            for gen in active:
                selected.append(pools[(source_split, gen)].pop())
                if len(selected) == count:
                    break
        return selected
    manifest = []
    for split, source_split, each in [('train', 'train', args.train_per_class), ('validation', 'train', args.eval_per_class), ('calibration', 'train', args.eval_per_class), ('test', 'validation', args.test_per_class), ('ood', 'validation', 100)]:
        rows = take(source_split, each, False) + take(source_split, each, True, split == 'ood')
        rng.shuffle(rows)
        for row in rows:
            suffix = Path(row['source_file']).suffix.lower()
            relative = f"images/{row['source_split']}-{row['index']:05d}{suffix}"
            path = output / relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(row['blob'])
            manifest.append({k: v for k, v in row.items() if k not in {'blob', 'index'}} | dict(path=relative, split=split))
    with (output / 'manifest.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    audit = dict(seed=42, held_out_generator='Midjourney', counts=dict(Counter(r['split'] for r in manifest)), generators={s: dict(Counter(r['generator'] for r in manifest if r['split'] == s)) for s in ['train','validation','calibration','test','ood']}, removed=dict(rejected), duplicate_policy='Global source filename, decoded RGB SHA256 and pHash Hamming <=4; later copies removed.', limitations=['Fixed first shards are not representative random samples of full GenImage; SD14 absent.', 'Source filenames retained but parent prompt/scene families unavailable; semantic identity leakage cannot be ruled out.', 'ImageNet-pretrained encoders may have seen real source images during pretraining.', 'Original mirror validation reserved for final test/OOD only.'], provenance=json.loads((source / 'download_manifest.json').read_text()))
    Path('research/results').mkdir(parents=True, exist_ok=True)
    audit['excluded_prior_manifest'] = [str(p) for p in args.exclude_manifest or []]
    audit['limitations'][0] = 'Fixed disclosed shards are not a representative random sample of full GenImage; see generator counts for coverage.'
    (output / 'preparation.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    Path(f'research/results/{output.name}_preparation.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k != 'provenance'}, indent=2))


if __name__ == '__main__':
    main()

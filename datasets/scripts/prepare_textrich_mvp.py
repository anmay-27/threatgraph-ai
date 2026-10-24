"""Pinned, reproducible modern-image development set; prior poster test excluded."""
import csv
import hashlib
import io
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
import requests
import numpy as np
from scipy.fft import dctn
from PIL import Image, ImageOps

ROOT = Path('datasets/prepared/textrich-mvp')
REPO = 'Shuyiww/TextRich'
CATEGORIES = ['CommercialPosters', 'InfographicCharts', 'Receipts', 'Tables', 'UIScreenshots']

def fingerprint(path):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        digest = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
        coef = dctn(np.asarray(image.convert('L').resize((32,32)),dtype=float))[:8,:8]
        phash = int(''.join('1' if b else '0' for b in (coef > np.median(coef)).flat),2)
    return digest, phash

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT/'manifest.csv').exists():
        print('Immutable dataset already prepared', flush=True); return
    source_file = ROOT/'source.json'
    if source_file.exists():
        revision = json.loads(source_file.read_text())['revision']
    else:
        response = requests.get(f'https://huggingface.co/api/datasets/{REPO}',timeout=30); response.raise_for_status()
        revision = response.json()['sha']
        source_file.write_text(json.dumps({'repository': REPO, 'revision': revision, 'categories': CATEGORIES, 'seed': 20261023, 'source': f'https://huggingface.co/datasets/{REPO}', 'limitations': 'Synthetic samples are GPT-Image-2 only; real samples retain upstream licenses. Unknown encoder pretraining overlap.'},indent=2))
    prior = Path('datasets/external/textrich-commercial-posters')
    old = list(csv.DictReader((prior/'manifest.csv').open()))
    excluded = {r['source_path'] for r in old}
    pixels, hashes = set(), []
    for row in old:
        digest, phash = fingerprint(prior/row['path']); pixels.add(digest); hashes.append(phash)
    selected = []
    rng = random.Random(20261023)
    for category in CATEGORIES:
        for label, folder in [(0,'0_real'),(1,'1_fake')]:
            url = f'https://huggingface.co/api/datasets/{REPO}/tree/{revision}/Data/{category}/{folder}?limit=1000'
            listing=[]
            while url:
                response=requests.get(url,timeout=45);response.raise_for_status()
                listing.extend(x for x in response.json() if x['type']=='file' and x['path'] not in excluded and x.get('size',0)<=8_000_000)
                url=response.links.get('next',{}).get('url')
            listing.sort(key=lambda x:x['path']);rng.shuffle(listing)
            if len(listing)<120: raise ValueError(f'Insufficient samples: {category}/{folder}')
            selected.extend(dict(item, label=label,category=category) for item in listing[:120])
    def download(item):
        target=ROOT/'images'/item['category']/str(item['label'])/Path(item['path']).name
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists() or target.stat().st_size != item['size']:
            response=requests.get(f'https://huggingface.co/datasets/{REPO}/resolve/{revision}/{quote(item["path"],safe="/")}',timeout=90);response.raise_for_status()
            if len(response.content)>8_000_000: raise ValueError('Oversized image')
            target.write_bytes(response.content)
        return item,target
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,(item,target) in enumerate(pool.map(download,selected),1):
            digest,phash=fingerprint(target)
            if digest in pixels or any((phash^old).bit_count()<=4 for old in hashes): continue
            pixels.add(digest);hashes.append(phash)
            rows.append({'path':target.relative_to(ROOT).as_posix(),'label':item['label'],'category':item['category'],'source_path':item['path'],'pixel_hash':digest,'phash':f'{phash:016x}','sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
            if i%50==0: print(f'downloaded and deduplicated {i}/1200',flush=True)
    for category in CATEGORIES:
        for label in [0,1]:
            group=[r for r in rows if r['category']==category and r['label']==label]
            rng.shuffle(group)
            for i,row in enumerate(group): row['split']='train' if i<int(len(group)*.6) else 'calibration' if i<int(len(group)*.8) else 'test'
    with (ROOT/'manifest.csv').open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({'count':len(rows),'splits':{s:sum(r['split']==s for r in rows) for s in ['train','calibration','test']}}),flush=True)

if __name__=='__main__': main()

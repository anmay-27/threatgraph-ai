"""Build immutable 10k training split from pinned shards, excluding prior experiments."""
import csv
import hashlib
import io
import json
import random
from collections import Counter,defaultdict
from pathlib import Path
import pyarrow.parquet as pq
import numpy as np
from scipy.fft import dctn
from PIL import Image,ImageOps

ROOT=Path('datasets/prepared/image-10k')
RAW=Path('datasets/raw/genimage-10k')
GENERATORS=['Real','ADM','BigGAN','GLIDE','Midjourney','SD14','SD15','VQDM','Wukong']

def main():
    if (ROOT/'manifest.csv').exists():raise RuntimeError('Immutable dataset already prepared')
    ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'images').mkdir(exist_ok=True)
    pixels=set();groups=set();hashes=set()
    # Deduplicate all earlier experimental examples, including their test sets.
    prior=list(Path('datasets/prepared').glob('*/manifest.csv'))+list(Path('datasets/external').glob('*/manifest.csv'))
    for manifest in prior:
        for row in csv.DictReader(manifest.open(encoding='utf-8-sig')):
            if row.get('pixel_hash'):pixels.add(row['pixel_hash'])
            if row.get('group'):groups.add(row['group'])
            if row.get('phash'):hashes.add(int(row['phash'],16))
    # BK-tree Hamming search avoids quadratic near-duplicate comparisons.
    tree=None
    def insert(value):
        nonlocal tree
        if tree is None:tree=[value,{}];return
        node=tree
        while True:
            distance=(value^node[0]).bit_count()
            if distance==0:return
            if distance not in node[1]:node[1][distance]=[value,{}];return
            node=node[1][distance]
    def near(value):
        stack=[tree] if tree else []
        while stack:
            node=stack.pop();distance=(value^node[0]).bit_count()
            if distance<=4:return True
            stack.extend(child for edge,child in node[1].items() if distance-4<=edge<=distance+4)
        return False
    for value in sorted(hashes):insert(value)
    candidates=[];removed=Counter()
    for shard in sorted(RAW.glob('*.parquet')):
        source='validation' if shard.name.startswith('validation') else 'train'
        for batch in pq.ParquetFile(shard).iter_batches(batch_size=16):
            for row in batch.to_pylist():
                generator=GENERATORS[row['generator']];group=generator+':'+Path(row['image']['path']).name.lower()
                if group in groups:removed['identity']+=1;continue
                blob=row['image']['bytes']
                with Image.open(io.BytesIO(blob)) as original:
                    image=ImageOps.exif_transpose(original).convert('RGB')
                    digest=hashlib.sha256(str(image.size).encode()+image.tobytes()).hexdigest()
                    coef=dctn(np.asarray(image.convert('L').resize((32,32)),dtype=float))[:8,:8]
                    phash=int(''.join('1' if x else '0' for x in (coef>np.median(coef)).flat),2)
                if digest in pixels or near(phash):removed['duplicate']+=1;continue
                groups.add(group);pixels.add(digest);insert(phash)
                suffix=Path(row['image']['path']).suffix.lower()
                relative=f'images/{digest}{suffix}'
                (ROOT/relative).write_bytes(blob)
                candidates.append(dict(path=relative,label=int(row['label']),generator=generator,group=group,pixel_hash=digest,phash=f'{phash:016x}',sha256=hashlib.sha256(blob).hexdigest(),source_split=source,source_shard=shard.name))
        print(f'Prepared {shard.name}; {len(candidates)} unique images',flush=True)
    rng=random.Random(20261025);pools=defaultdict(list)
    for row in candidates:pools[(row['source_split'],row['label'],row['generator'])].append(row)
    for pool in pools.values():rng.shuffle(pool)
    def take(source,label,count,heldout=False):
        gens=['Real'] if label==0 else ['Midjourney'] if heldout else [g for g in GENERATORS[1:] if g!='Midjourney']
        result=[]
        while len(result)<count:
            active=[g for g in gens if pools[(source,label,g)]]
            if not active:raise ValueError(f'Insufficient unique examples for {source}/{label}: {len(result)}/{count}')
            for g in active:
                result.append(pools[(source,label,g)].pop())
                if len(result)==count:break
        return result
    result=[]
    for split,source,count in [('train','train',5000),('validation','train',500),('calibration','train',500),('test','validation',500),('ood','validation',100)]:
        for label in [0,1]:
            for row in take(source,label,count,split=='ood'):result.append(dict(row,split=split))
    with (ROOT/'manifest.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(result[0]));writer.writeheader();writer.writerows(result)
    audit={'counts':dict(Counter(r['split'] for r in result)),'removed':dict(removed),'prior_manifests':[str(p) for p in prior],'source':json.loads((RAW/'download_manifest.json').read_text()),'limitations':['Research-only source license; not permission for commercial redistribution.','Unknown upstream model pretraining overlap.','Fresh local held-out sets are not independent real-world validation.']}
    (ROOT/'preparation.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit['counts']),flush=True)

if __name__=='__main__':main()

"""10k+ training experiment. Never installs a candidate or changes release gates."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import train_image_mvp as experiment

def rows(legacy_only=False):
    result=[]
    for source,root in [('legacy',Path('datasets/prepared/image-10k')),('modern',Path('datasets/prepared/textrich-mvp')),('poster',Path('datasets/external/textrich-commercial-posters'))]:
        for row in csv.DictReader((root/'manifest.csv').open(encoding='utf-8-sig')):
            split=row.get('split','test')
            if source=='modern' and split=='train' and int(row['sha256'][:8],16)%5==0:split='validation'
            result.append({'path':str(root/row['path']),'label':int(row['label']),'split':split,'source':source,'category':row.get('category',row.get('generator','poster'))})
    assert sum(r['split']=='train' for r in result)>=10000
    return result

if __name__=='__main__':
    experiment.OUT=Path('research/experiments/image-10k')
    experiment.rows=rows
    experiment.main()

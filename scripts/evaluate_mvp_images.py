"""Frozen-threshold diagnostic evaluation. Never trains or activates a model."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ml.common.openfake_image import infer

def summarize(rows):
    real=[r for r in rows if r['label']==0]; ai=[r for r in rows if r['label']==1]
    return dict(count=len(rows), genuine=len(real), synthetic=len(ai),
                false_ai_accusations=sum(r['verdict']=='likely_ai_generated' for r in real),
                missed_ai=sum(r['verdict']=='likely_real' for r in ai),
                ai_not_detected=sum(r['verdict']!='likely_ai_generated' for r in ai),
                inconclusive=sum(r['verdict'] not in ('likely_ai_generated','likely_real') for r in rows),
                correct_conclusive=sum((r['label']==1 and r['verdict']=='likely_ai_generated') or (r['label']==0 and r['verdict']=='likely_real') for r in rows))

def main():
    out=ROOT/'research/results/mvp-image-evaluation';out.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'research/experiments/image-diversity-v1/features.json').read_text())['rows']
    old=json.loads((ROOT/'research/experiments/openfake-pretrained/predictions.json').read_text())
    excluded={hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest() for r in old}
    selected=[]; seen=set(excluded)
    for source in ('poster','modern','diverse'):
        for label in (0,1):
            count=0
            for row in sorted((r for r in rows if r['source']==source and r['label']==label and r['split']=='test'),key=lambda r:r['path']):
                digest=hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()
                if digest in seen:continue
                seen.add(digest);selected.append(dict(row,sha256=digest));count+=1
                if count==30:break
    checkpoint=ROOT/'models/image/detectra-openfake/model.onnx'
    (out/'manifest.json').write_text(json.dumps(dict(checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),rows=selected),indent=2))
    results=[]
    for row in selected:
        results.append(dict(row,**infer(ROOT/row['path'],checkpoint)))
        if len(results)%10==0:print(f'Evaluated {len(results)}/{len(selected)}',flush=True)
    report=dict(overall=summarize(results),groups={s:summarize([r for r in results if r['source']==s]) for s in ('poster','modern','diverse')},
                limitation='Additional samples from existing local research test partitions, excluding previous OpenFake benchmark hashes. Not independent field validation; upstream training overlap unknown. Edited-image and generator-specific coverage requires further labeled data. No thresholds changed.',threshold=.95)
    (out/'predictions.json').write_text(json.dumps(results,indent=2))
    (out/'metrics.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()

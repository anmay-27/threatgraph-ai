"""Fixed diagnostic benchmark; no fitting, threshold search or automatic activation."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ml.common.openfake_image import infer
from ml.common.metrics import metrics


def main():
    checkpoint=ROOT/'models/image/detectra-openfake/model.onnx'
    output=ROOT/'research/experiments/openfake-pretrained'
    output.mkdir(parents=True,exist_ok=True)
    if (output/'metrics.json').exists():raise RuntimeError('Benchmark finalized')
    rows=json.loads((ROOT/'research/experiments/image-diversity-v1/features.json').read_text())['rows']
    selected=[]
    for source in ('poster','modern','diverse'):
        for label in (0,1):
            pool=sorted((r for r in rows if r['source']==source and r['label']==label and r['split']=='test'),key=lambda r:r['path'])
            selected.extend(pool[:20])
    results=[]
    user=[]
    for name in ('photo beard.jpeg','WhatsApp Image 2026-10-06 at 20.18.59.jpeg'):
        path=Path('C:/Users/DELL/Downloads')/name
        if path.exists():
            result=infer(path,checkpoint);user.append(dict(name=name,**result))
            print(name,result['probability'],result['verdict'],flush=True)
    (output/'user-regression.json').write_text(json.dumps(user,indent=2))
    for row in selected:
        result=infer(ROOT/row['path'],checkpoint)
        results.append(dict(**row,**result))
        (output/'predictions.json').write_text(json.dumps(results,indent=2))
        if len(results)%10==0:print(f'Benchmark {len(results)}/{len(selected)}',flush=True)
    summary=dict(candidate={},count=len(results),threshold=.95,installed=False,limitations='Small previously examined local research sets; upstream training overlap unknown. No claim of independent field accuracy. User examples excluded from fitting and benchmark metrics.')
    for source in ('poster','modern','diverse'):
        group=[r for r in results if r['source']==source]
        summary['candidate'][source]=metrics([r['label'] for r in group],[r['probability'] for r in group],.95)
    (output/'metrics.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()

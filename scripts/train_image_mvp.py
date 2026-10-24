"""Train a regularized residual classifier on a frozen Community Forensics encoder.

Validation chooses regularization. Calibration chooses temperature/cutoff.
Modern test, legacy test/OOD and prior posters are never used for fitting.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset, DataLoader
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.common import community_image
from ml.common.metrics import metrics

OUT=Path('research/experiments/image-mvp-residual')
CHECKPOINT=Path('models/image/community-forensics-384/model.safetensors')

def rows(legacy_only=False):
    result=[]
    for source,root in [('legacy',Path('datasets/prepared/tiny-genimage-v4')),('modern',Path('datasets/prepared/textrich-mvp')),('poster',Path('datasets/external/textrich-commercial-posters'))]:
        if legacy_only and source != 'legacy': continue
        for row in csv.DictReader((root/'manifest.csv').open(encoding='utf-8-sig')):
            split=row.get('split','test')
            # Fixed hash split within modern training only; no calibration/test reuse.
            if source=='modern' and split=='train' and int(row['sha256'][:8],16)%5==0: split='validation'
            result.append({'path':str(root/row['path']),'label':int(row['label']),'split':split,'source':source,'category':row.get('category',row.get('generator','poster'))})
    return result

class Images(Dataset):
    def __init__(self,items):self.items=items
    def __len__(self):return len(self.items)
    def __getitem__(self,index):
        with Image.open(self.items[index]['path']) as image:return community_image.image_tensor(image)

def sigmoid(z):return 1/(1+np.exp(-np.clip(z,-50,50)))
def nll(y,z):return float(np.mean(np.logaddexp(0,z)-y*z))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'metrics.json').exists():raise ValueError('Experiment finalized; do not optimize on its test results')
    legacy_only='--cache-legacy' in sys.argv
    items=rows(legacy_only)
    fingerprint=hashlib.sha256(json.dumps(items,sort_keys=True).encode()+CHECKPOINT.read_bytes()).hexdigest()
    metadata=OUT/'features.json'
    metadata.write_text(json.dumps({'fingerprint':fingerprint,'rows':items},indent=2))
    model=community_image.load(str(CHECKPOINT),CHECKPOINT.stat().st_mtime_ns)
    chunks=[]
    with torch.inference_mode():
        for start in range(0,len(items),100):
            key=hashlib.sha256(json.dumps(items[start:start+100],sort_keys=True).encode()+str(CHECKPOINT.stat().st_mtime_ns).encode()).hexdigest()[:20]
            cache=OUT/f'features-{key}.npz'
            if cache.exists():
                chunk=np.load(cache);chunks.append((chunk['x'],chunk['z']));continue
            x,z=[],[]
            for batch in DataLoader(Images(items[start:start+100]),batch_size=4,num_workers=0):
                embedding=model.forward_head(model.forward_features(batch),pre_logits=True)
                x.extend(embedding.numpy());z.extend(model.head(embedding).reshape(-1).numpy())
            np.savez_compressed(cache,x=np.asarray(x),z=np.asarray(z))
            chunks.append((np.asarray(x),np.asarray(z)))
            print(f'Encoder features: {min(start+100,len(items))}/{len(items)}',flush=True)
    if legacy_only:
        print('Legacy encoder feature cache complete',flush=True);return
    x=np.concatenate([c[0] for c in chunks]).astype(np.float64)
    z=np.concatenate([c[1] for c in chunks]).astype(np.float64)
    y=np.array([r['label'] for r in items])
    split=np.array([r['split'] for r in items]);source=np.array([r['source'] for r in items])
    train=split=='train';val=split=='validation';cal=split=='calibration'
    mean=x[train].mean(axis=0);scale=np.maximum(x[train].std(axis=0),.01)
    standardized=(x-mean)/scale
    tx=torch.tensor(standardized[train],dtype=torch.float64);tz=torch.tensor(z[train]);ty=torch.tensor(y[train],dtype=torch.float64)
    candidates=[]
    for penalty in [.1,1.,10.]:
        w=torch.zeros(x.shape[1],dtype=torch.float64,requires_grad=True)
        b=torch.zeros((),dtype=torch.float64,requires_grad=True)
        optimizer=torch.optim.LBFGS([w,b],max_iter=100,line_search_fn='strong_wolfe')
        def closure():
            optimizer.zero_grad();loss=torch.nn.functional.binary_cross_entropy_with_logits(tz+tx@w+b,ty)+penalty*(w.square().sum()+b.square())
            loss.backward();return loss
        optimizer.step(closure)
        weight=w.detach().numpy();bias=float(b.detach())
        logits=z+standardized@weight+bias
        candidates.append((nll(y[val],logits[val]),penalty,weight,bias,logits))
    _,penalty,weight,bias,logits=min(candidates,key=lambda row:row[0])
    temperature=float(min(np.geomspace(.25,8,40),key=lambda t:nll(y[cal],logits[cal]/t)))
    p=sigmoid(logits/temperature)
    thresholds=[(float(t),metrics(y[cal],p[cal],t)) for t in np.linspace(.01,.99,99)]
    eligible=[(t,m) for t,m in thresholds if m['false_positive_rate']<=.05]
    threshold=max(eligible,key=lambda pair:(pair[1]['balanced_accuracy'],pair[1]['recall'],pair[0]))[0] if eligible else 1.
    adapter={'schema':1,'base_sha256':hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest(),'mean':mean.tolist(),'scale':scale.tolist(),'weights':weight.tolist(),'bias':bias,'temperature':temperature,'threshold':threshold,'penalty':penalty,'fit_count':int(train.sum()),'calibration_count':int(cal.sum()),'feature_fingerprint':fingerprint}
    (OUT/'adapter.json').write_text(json.dumps(adapter,indent=2))
    baseline=json.loads(CHECKPOINT.with_name('calibration.json').read_text())
    bp=sigmoid(z/baseline['temperature'])
    result={'training_count':int(train.sum()),'validation_count':int(val.sum()),'calibration_count':int(cal.sum()),'total_images':len(items),'candidate':{},'baseline':{},'limits':['One modern synthetic generator; not representative field accuracy.','Potential unknown overlap with upstream encoder pretraining.','Single original-view comparison; deployment also checks transform stability.']}
    for name,mask in [('legacy_test',(source=='legacy')&(split=='test')),('legacy_ood',(source=='legacy')&(split=='ood')),('modern_test',(source=='modern')&(split=='test')),('prior_posters',source=='poster')]:
        result['candidate'][name]=metrics(y[mask],p[mask],threshold)
        result['baseline'][name]=metrics(y[mask],bp[mask],baseline['threshold'])
    c,o=result['candidate'],result['baseline']
    passed=c['modern_test']['balanced_accuracy']>=o['modern_test']['balanced_accuracy']+.02 and all(c[k]['balanced_accuracy']>=o[k]['balanced_accuracy']-.02 and c[k]['false_positive_rate']<=max(.05,o[k]['false_positive_rate']) for k in c)
    result['deployment_gate_passed']=bool(passed)
    result['decision']='Candidate eligible for transform-stability validation; not automatically installed' if passed else 'Rejected: retain existing production detector'
    result['gate']='Modern balanced accuracy improves >=2 points; no other test loses >2 points; each FPR <= max(5%,baseline).'
    (OUT/'metrics.json').write_text(json.dumps(result,indent=2))
    (OUT/'predictions.json').write_text(json.dumps([dict(row,baseline=float(a),candidate=float(b)) for row,a,b in zip(items,bp,p)],indent=2))
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()

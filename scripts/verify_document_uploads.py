"""Live upload regression: PDF, DOCX, and a generated video above the old 25 MB cap."""
import json
import time
import zipfile
from pathlib import Path
import requests
import fitz
import cv2
import numpy as np

out=Path('research/results/document-upload-check');out.mkdir(parents=True,exist_ok=True)
base='http://127.0.0.1:8000/api/v1'
health=requests.get(base+'/health',timeout=10).json()
assert health['max_upload_mb']==250,health
pdf=out/'readable.pdf'
with fitz.open() as doc:
    page=doc.new_page();page.insert_text((40,40),'Quarterly report: project milestones completed.');doc.save(pdf)
office=out/'readable.docx'
with zipfile.ZipFile(office,'w') as z:
    z.writestr('[Content_Types].xml','<Types/>')
    z.writestr('word/document.xml','<document><t>Quarterly report. Project milestones completed.</t></document>')
video=out/'large-video.avi'
writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),24,(640,480))
assert writer.isOpened()
rng=np.random.default_rng(42)
for _ in range(180):writer.write(rng.integers(0,256,(480,640,3),dtype=np.uint8))
writer.release()
assert video.stat().st_size>25*1024*1024
results=[]
for path in [pdf,office,video]:
    with path.open('rb') as f:
        response=requests.post(base+'/analyze/file',files={'file':(path.name,f)},timeout=90)
    response.raise_for_status();identifier=response.json()['id']
    for _ in range(180):
        row=requests.get(base+'/analyses/'+identifier,timeout=10).json()
        if row['state'] not in ['QUEUED','PROCESSING']:break
        time.sleep(2)
    assert row['state'] in ['COMPLETED','PARTIAL'],row['state']
    labels={e['label'] for e in row['report']['evidence']}
    assert ('video_metadata' if path==video else 'document_summary') in labels,labels
    assert 'no_signature_match' in labels,labels
    if path!=video:
        exported=requests.get(base+'/analyses/'+identifier+'/report.pdf',timeout=30)
        exported.raise_for_status()
        with fitz.open(stream=exported.content,filetype='pdf') as document:
            text=' '.join(page.get_text() for page in document)
            assert 'Document investigation' in text and 'Quarterly report' in text
    results.append({'file':path.name,'bytes':path.stat().st_size,'id':identifier,'state':row['state'],'labels':sorted(labels)})
    print(json.dumps(results[-1]),flush=True)
(out/'validation.json').write_text(json.dumps({'max_upload_mb':health['max_upload_mb'],'results':results,'passed':True},indent=2))

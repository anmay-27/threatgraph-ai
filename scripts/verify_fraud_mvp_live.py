"""Real local API/browser verification with fictional inputs, no mocked findings."""
import json
import time
from pathlib import Path
import requests
import fitz

BASE='http://127.0.0.1:8000/api/v1'
OUT=Path('research/results/fraud-mvp-live')


def call(method,path,**kwargs):
    r=requests.request(method,BASE+path,timeout=30,**kwargs);r.raise_for_status();return r


def upload(path,case):
    with path.open('rb') as f:
        aid=call('POST','/analyze/file',files={'file':(path.name,f,'application/octet-stream')}).json()['id']
    call('POST',f'/cases/{case}/analyses/{aid}')
    for _ in range(150):
        row=call('GET','/analyses/'+aid).json()
        if row['state'] in ('COMPLETED','PARTIAL','FAILED'):
            assert row['state']!='FAILED',row.get('error')
            return row
        time.sleep(1)
    raise TimeoutError(aid)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    old=call('POST','/cases',json={'title':'DEMO - Previous payment report','description':'Fictional correlation input; not a real allegation.'}).json()['id']
    new=call('POST','/cases',json={'title':'DEMO - Suspicious recruitment offer','description':'Fictional email and PDF; live QR destination is benign example.com.'}).json()['id']
    (OUT/'ids.json').write_text(json.dumps(dict(previous_case=old,case=new)))
    prior=upload(Path('frontend/public/demo/previous-payment.txt'),old)
    incoming=upload(Path('frontend/public/demo/fictional-offer.eml'),new)
    detail=call('GET','/cases/'+new).json()
    assert any(s['scenario_name']=='recruitment_payment_chain' for s in detail['assessment']['scenarios'])
    assert any(c['entity_type']=='UPI_ID' and c['case_id']==old for c in detail['assessment']['correlations'])
    assert any(e['relation']=='resolves_to' for e in detail['graph']['edges'])
    assert any(e['label']=='qr_decoded' for e in incoming['report']['evidence'])
    assert any(e['label']=='email_headers' for e in incoming['report']['evidence'])
    pdf=call('GET',f'/cases/{new}/report.pdf').content
    (OUT/'case-report.pdf').write_bytes(pdf)
    with fitz.open(stream=pdf,filetype='pdf') as doc:
        text=' '.join(p.get_text() for p in doc)
    assert 'recruitment-demo@demo' in text and 'Potential recruitment' in text
    # Delete only a newly created disposable verification upload/case.
    disposable=call('POST','/cases',json={'title':'Disposable deletion verification'}).json()['id']
    deletion=upload(Path('frontend/public/demo/previous-payment.txt'),disposable)
    call('DELETE',f"/analyses/{deletion['id']}/original")
    assert not call('GET',f"/analyses/{deletion['id']}/privacy").json()['original_present']
    call('DELETE',f"/analyses/{deletion['id']}")
    assert not call('GET','/cases/'+disposable).json()['analyses']
    call('DELETE','/cases/'+disposable)
    assert requests.get(BASE+'/cases/'+disposable).status_code==404
    (OUT/'case.json').write_text(json.dumps(detail,indent=2))
    summary=dict(case_id=new,previous_case_id=old,analysis_id=incoming['id'],state=incoming['state'],scenarios=len(detail['assessment']['scenarios']),correlations=len(detail['assessment']['correlations']),pdf_verified=True,deletion_verified=True,limitations='Fictional input. QR fetched real benign example.com, not a malicious payment endpoint. Exact hostile-page chain covered by controlled automated test.')
    (OUT/'verification.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()

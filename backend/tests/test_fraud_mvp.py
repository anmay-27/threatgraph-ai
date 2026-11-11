import asyncio
from email.message import EmailMessage
import cv2
import fitz
from fastapi.testclient import TestClient
from app.main import app, requests
from app.models.database import Analysis, Session
from app.core.fetch import FetchResult
from app.services.investigation import Investigation
from app.services.intelligence import index_analysis, extract_text
from app.services.scenarios import chain_scenarios
from app.schemas.evidence import finding
from app.threat_graph.graph import ThreatGraph


def test_rules_require_observed_path_not_unrelated_clues():
    graph=ThreatGraph();a=graph.node('file','email');b=graph.node('file','other')
    evidence=[finding(a,'message','metadata','recruitment_language','job'),finding(b,'message','metadata','advance_fee_request','fee')]
    assert chain_scenarios(evidence,graph)==[]
    graph.edge(a,b,'contains')
    assert chain_scenarios(evidence,graph)[0]['asset_path']==[a,b]


def test_job_email_pdf_qr_payment_case_and_export(monkeypatch,tmp_path):
    qr=cv2.QRCodeEncoder_create().encode('https://recruitment.example/payment')
    qr=cv2.copyMakeBorder(qr,4,4,4,4,cv2.BORDER_CONSTANT,value=255)
    qr=cv2.resize(qr,(420,420),interpolation=cv2.INTER_NEAREST)
    pdf=fitz.open();page=pdf.new_page();page.insert_text((40,40),'Candidate instructions: scan the QR to continue.')
    page.insert_image(fitz.Rect(40,100,460,520),stream=cv2.imencode('.png',qr)[1].tobytes())
    email=EmailMessage();email['From']='hr@recruitment.example';email['Subject']='Job offer';email.set_content('You have been selected for a job offer. See the attached instructions.')
    email.add_attachment(pdf.tobytes(),maintype='application',subtype='pdf',filename='instructions.pdf');pdf.close()
    path=tmp_path/'job.eml';path.write_bytes(email.as_bytes())
    seen=[]
    async def fetch(url,*args):
        seen.append(url)
        return FetchResult(url,b'<html><body>Registration fee: pay before onboarding. UPI ID: training@demo <a href="upi://pay?pa=training@demo">Pay</a></body></html>','text/html',[],200)
    monkeypatch.setattr('app.services.investigation.fetch',fetch)
    with TestClient(app) as client:
        requests.clear()
        previous=client.post('/api/v1/cases',json={'title':'Previous reported payment'}).json()['id']
        current=client.post('/api/v1/cases',json={'title':'Job offer investigation'}).json()['id']
        with Session() as db:
            earlier=Analysis(name='prior.txt',state='COMPLETED',report={'evidence':[{'id':'prior','metadata':{'text':'UPI ID: training@demo'}}]})
            incoming=Analysis(name='job.eml',state='PROCESSING');db.add_all([earlier,incoming]);db.commit();aid=incoming.id;pid=earlier.id
            index_analysis(db,earlier);db.commit()
        inv=Investigation(aid)
        try:
            asyncio.run(inv.file(path,'job.eml'));report=inv.report()
        finally:inv.temp.cleanup()
        assert seen==['https://recruitment.example/payment']
        chain=next(s for s in report['scenarios'] if s['scenario_name']=='recruitment_payment_chain')
        assert len(chain['asset_path'])>=4
        with Session() as db:
            row=db.get(Analysis,aid);row.report=report;row.state='PARTIAL';index_analysis(db,row);db.commit()
        for cid,identifier in ((previous,pid),(current,aid)):
            assert client.post(f'/api/v1/cases/{cid}/analyses/{identifier}').status_code==200
        data=client.get('/api/v1/cases/'+current).json()
        assert data['assessment']['scenarios']
        assert any(c['entity_type']=='UPI_ID' and c['case_id']==previous for c in data['assessment']['correlations'])
        assert any(e['relation']=='also_seen_in' for e in data['graph']['edges'])
        exported=client.get(f'/api/v1/cases/{current}/report.pdf');assert exported.status_code==200
        with fitz.open(stream=exported.content,filetype='pdf') as doc:
            text=' '.join(p.get_text() for p in doc)
        assert 'training@demo' in text and 'Potential recruitment' in text
        assert client.delete(f'/api/v1/cases/{previous}').status_code==200
        assert client.get('/api/v1/cases/'+current).json()['assessment']['correlations']==[]


def test_payment_handle_is_explicit():
    assert ('UPI_ID','person@demo') in extract_text('UPI ID: person@demo')
    assert not any(k=='UPI_ID' for k,v in extract_text('Email person@example.com'))


def test_public_ca_bundle_does_not_disable_tls_validation():
    import ssl
    from app.core.fetch import verified_tls_context
    context=verified_tls_context()
    assert context.verify_mode==ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.cert_store_stats()['x509_ca']>0


def test_high_synthetic_score_alone_does_not_raise_cyber_risk(monkeypatch):
    from app.fusion.engine import fuse
    monkeypatch.setattr('app.services.registry.registry',lambda:[{'name':'fusion','available':False}])
    evidence=finding('image','image_detector','synthetic_media','synthetic_probability','AI origin signal',.999,.99,hypothesis='synthetic_media')
    result=fuse([evidence],[])
    assert result['risk_score'] is None
    assert result['risk_level']=='UNKNOWN'
    assert result['contributions']==[]

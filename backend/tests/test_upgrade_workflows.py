import asyncio
from email.message import EmailMessage
import cv2
import fitz
from fastapi.testclient import TestClient
from app.main import app,requests
from app.models.database import Analysis,Session
from app.services.investigation import Investigation
from app.core.fetch import FetchResult


def test_email_pdf_qr_chain_uses_real_parsers_and_rules(tmp_path,monkeypatch):
    # Only network transport is replaced with a controlled fixture. PDF, QR,
    # email parsing, graph edges and scenario inference execute real code.
    qr=cv2.QRCodeEncoder_create().encode('https://controlled.example/payment')
    qr=cv2.copyMakeBorder(qr,4,4,4,4,cv2.BORDER_CONSTANT,value=255)
    qr=cv2.resize(qr,(400,400),interpolation=cv2.INTER_NEAREST)
    pdf=fitz.open();page=pdf.new_page();page.insert_text((40,40),'Job offer - registration fee requested before onboarding.')
    page.insert_image(fitz.Rect(50,100,450,500),stream=cv2.imencode('.png',qr)[1].tobytes())
    message=EmailMessage();message['From']='recruiter@controlled.example';message['Subject']='Job offer';message.set_content('Job offer: registration fee required. Verify this controlled test independently.')
    message.add_attachment(pdf.tobytes(),maintype='application',subtype='pdf',filename='offer.pdf');pdf.close()
    path=tmp_path/'offer.eml';path.write_bytes(message.as_bytes())
    seen=[]
    async def fixture_fetch(url,*args):
        seen.append(url)
        return FetchResult(url,b'<html>Microsoft verify immediately<form action="https://collector.example/"><input type="password"></form></html>','text/html',[],200)
    monkeypatch.setattr('app.services.investigation.fetch',fixture_fetch)
    with TestClient(app):
        with Session() as db:
            row=Analysis(name='offer.eml');db.add(row);db.commit();identifier=row.id
        inv=Investigation(identifier)
        try:
            asyncio.run(inv.file(path,'offer.eml'))
            report=inv.report()
            assert seen==['https://controlled.example/payment']
            assert any(s['scenario_name']=='recruitment_scam' for s in report['scenarios'])
            assert any(s['label']=='Potential QR phishing' for s in report['scenarios'])
            assert any(e['relation']=='resolves_to' for e in report['graph']['edges'])
        finally:inv.temp.cleanup()


def test_feedback_duplicates_and_cancellation():
    with TestClient(app) as client:
        requests.clear()
        with Session() as db:
            rows=[Analysis(name='same.txt',sha256='a'*64,state='COMPLETED',report={'evidence':[{'id':'finding-1'}]}) for _ in range(2)]
            db.add_all(rows);db.commit();aid,bid=[r.id for r in rows]
        assert client.get(f'/api/v1/analyses/{aid}/duplicates').json()['matches'][0]['id']==bid
        assert client.post(f'/api/v1/analyses/{aid}/feedback',json={'evidence_id':'missing','verdict':'incorrect'}).status_code==422
        assert client.post(f'/api/v1/analyses/{aid}/feedback',json={'evidence_id':'finding-1','verdict':'unsure'}).json()['used_for_training'] is False
        assert client.post(f'/api/v1/analyses/{aid}/cancel').status_code==409
        with Session() as db:
            row=Analysis(name='cancel.txt',state='QUEUED');db.add(row);db.commit();cancel_id=row.id
        assert client.post(f'/api/v1/analyses/{cancel_id}/cancel').status_code==200
        from app.services.investigation import run
        run(cancel_id)
        assert client.get(f'/api/v1/analyses/{cancel_id}').json()['state']=='CANCELLED'

"""Browser/API verification for the seven MVP improvements; no detector stubs."""
import json
from pathlib import Path
import requests
import fitz
from playwright.sync_api import sync_playwright

OUT=Path('research/results/mvp-polish');OUT.mkdir(parents=True,exist_ok=True)
base='http://127.0.0.1:8000/api/v1'
ids=json.loads(Path('research/results/fraud-mvp-live/verification.json').read_text())
detail=requests.get(base+'/cases/'+ids['case_id'],timeout=10).json()
aid=next(a['id'] for a in detail['analyses'] if a['name']=='fictional-offer.eml')
row=requests.get(base+'/analyses/'+aid,timeout=10).json()
assert row['report']['decision_summary']['scenarios']
pdf=requests.get(base+'/analyses/'+aid+'/report.pdf',timeout=30);pdf.raise_for_status()
(OUT/'investigation.pdf').write_bytes(pdf.content)
with fitz.open(stream=pdf.content,filetype='pdf') as doc:
    assert 'Decision brief' in doc[0].get_text()
    assert 'Next:' in doc[0].get_text()
    doc[0].get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(str(OUT/'pdf-first-page.png'))
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:3000/analysis/'+aid)
    page.get_by_role('region',name='Investigation conclusion').wait_for()
    page.screenshot(path=str(OUT/'result-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function('document.documentElement.scrollWidth <= innerWidth+1',timeout=10000)
    page.screenshot(path=str(OUT/'result-mobile.png'),full_page=True)
    page.goto('http://127.0.0.1:3000/analyze')
    page.get_by_text('Before you investigate',exact=False).click()
    page.get_by_role('region',name='Before you investigate').get_by_text('Malware signatures',exact=False).wait_for()
    page.goto('http://127.0.0.1:3000/research/models')
    page.get_by_role('heading',name='Image model: measured limitations').wait_for()
    page.get_by_text('30/30 AI images flagged').wait_for()
    page.goto('http://127.0.0.1:3000/demo')
    page.get_by_role('heading',name='Demo acceptance checklist').wait_for()
    assert not errors,errors
    browser.close()
(OUT/'verification.json').write_text(json.dumps(dict(analysis_id=aid,case_id=ids['case_id'],summary=True,pdf_first_page=True,mobile=True,readiness=True,benchmark=True,demo=True,browser_errors=errors),indent=2))
print('MVP polish verification passed')

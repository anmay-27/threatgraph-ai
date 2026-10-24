"""UI/PDF smoke check of a completed local URL investigation."""
import json
import sys
from pathlib import Path
import requests
import fitz
from playwright.sync_api import sync_playwright

identifier=sys.argv[1]
out=Path('research/results/mvp-report');out.mkdir(parents=True,exist_ok=True)
row=requests.get(f'http://127.0.0.1:8000/api/v1/analyses/{identifier}',timeout=20).json()
assert row['state'] in {'COMPLETED','PARTIAL'}
summary=row['report']['url_summary']
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page()
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    for label,width,height in [('desktop',1440,1000),('mobile',390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        page.goto(f'http://127.0.0.1:3000/analysis/{identifier}')
        page.get_by_role('heading',name=summary['title'],exact=True).wait_for(timeout=30000)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),label+' horizontal overflow'
        assert 'reached https://www.w3.org/2000/svg' not in page.locator('body').inner_text()
        page.screenshot(path=str(out/f'{label}.png'),full_page=False)
    assert not errors,errors
    browser.close()
response=requests.get(f'http://127.0.0.1:8000/api/v1/analyses/{identifier}/report.pdf',timeout=90)
response.raise_for_status();(out/'investigation.pdf').write_bytes(response.content)
document=fitz.open(stream=response.content,filetype='pdf')
text=' '.join(' '.join(page.get_text().split()) for page in document)
assert summary['title'] in text
assert 'email, name, phone, student identifier' in text
assert 'Malware signatures - completed' in text
overflow=[]
for index,page in enumerate(document):
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            for span in line.get('spans',[]):
                if span['bbox'][2]>555:overflow.append({'page':index+1,'right':span['bbox'][2]})
assert not overflow,overflow
document[0].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(str(out/'pdf-page-1.png'))
result={'analysis':identifier,'ui_widths':[1440,390],'console_errors':errors,'pdf_pages':len(document),'overflow':overflow,'passed':True}
(out/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

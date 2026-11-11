"""Exercise the running UI using the saved live-verification case."""
import json
import time
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    root=Path('research/results/fraud-mvp-live')
    result=json.loads((root/'verification.json').read_text())
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:3000/cases/'+result['case_id'])
        page.get_by_role('heading',name='Potential fraud chain requires review').wait_for()
        upload=page.locator('input[type=file]')
        upload.set_input_files({'name':'empty.txt','mimeType':'text/plain','buffer':b''})
        page.get_by_text('Empty file',exact=False).wait_for()
        upload.set_input_files({'name':'ui-upload-verification.txt','mimeType':'text/plain','buffer':b'Fictional interface verification. No threat assertion.'})
        page.get_by_text('Investigation added. Results update here as checks finish.').wait_for()
        base='http://127.0.0.1:8000/api/v1'
        detail=requests.get(base+'/cases/'+result['case_id'],timeout=10).json()
        uploaded=next(a for a in detail['analyses'] if a['name']=='ui-upload-verification.txt')
        for _ in range(90):
            state=requests.get(base+'/analyses/'+uploaded['id'],timeout=10).json()['state']
            if state not in ('QUEUED','PROCESSING'):break
            time.sleep(1)
        assert state!='FAILED'
        response=requests.delete(base+'/analyses/'+uploaded['id'],timeout=10);response.raise_for_status()
        page.reload();page.get_by_role('heading',name='Potential fraud chain requires review').wait_for()
        page.locator('a[href="/cases/'+result['previous_case_id']+'"]').first.wait_for()
        page.get_by_role('button',name='Switch to analyst view').click()
        assert page.get_by_text('Evidence references:',exact=False).count()>0
        page.get_by_role('tab',name='Threat graph',exact=True).click()
        page.screenshot(path=str(root/'case-desktop.png'),full_page=True)
        with page.expect_download() as download:
            page.get_by_role('link',name='Export case PDF').click()
        download.value.save_as(str(root/'browser-case-report.pdf'))
        page.set_viewport_size({'width':390,'height':844})
        page.get_by_role('button',name='Switch to simple view').click()
        page.screenshot(path=str(root/'case-mobile.png'),full_page=True)
        width=page.evaluate('({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})')
        assert width['scroll']<=width['client']+2,width
        page.goto('http://127.0.0.1:3000/demo')
        page.get_by_role('heading',name='Primary demo: investigate a suspicious job offer').wait_for()
        with page.expect_download() as download:
            page.get_by_role('link',name='the email with its PDF attachment').click()
        assert download.value.suggested_filename=='fictional-offer.eml'
        browser.close()
    assert not errors,errors
    (root/'ui-verification.json').write_text(json.dumps(dict(desktop=True,mobile=True,analyst_toggle=True,case_upload=True,empty_upload_failure=True,case_pdf_download=True,fictional_email_download=True,js_errors=errors),indent=2))
    print('Live UI checks passed')


if __name__=='__main__':main()

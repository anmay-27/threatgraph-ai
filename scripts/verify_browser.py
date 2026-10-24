"""Live browser regression with mocked public responses, no external page access."""
import asyncio
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from app.analyzers.url.browser import inspect_browser
from app.core.fetch import FetchResult,normalize_url

async def main():
    fetched=[]
    async def mock_fetch(url,max_bytes):
        normalize_url(url)
        fetched.append(url)
        if url!='https://example.com/app.js':raise ValueError('Unexpected mock resource')
        body=b'''document.querySelector('form').innerHTML='<label for="phone">Mobile number</label><input id="phone">';
fetch('http://127.0.0.1/private').catch(()=>{});fetch('https://example.com/submit',{method:'POST',body:'test'}).catch(()=>{});
try { new WebSocket('wss://example.com/ws'); } catch(e) {}'''
        return FetchResult(url,body,'application/javascript',[],200)
    result=await inspect_browser(b'<html><form method="post"></form><script src="https://example.com/app.js"></script></html>','https://example.com/',fetcher=mock_fetch)
    rendered=result.pop('html').decode()
    assert 'Mobile number' in rendered
    assert fetched==['https://example.com/app.js']
    assert any(r['method']=='POST' and r['status']=='blocked' for r in result['requests'])
    assert any(r['host']=='127.0.0.1' and r['status']=='blocked' for r in result['requests'])
    result['passed']=True
    Path('research/results/browser_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
asyncio.run(main())

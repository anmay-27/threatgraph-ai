"""Optional bounded, unauthenticated browser observation through the guarded fetcher.

Browser network uses a deliberately unavailable proxy. Only intercepted GET
resources are fulfilled by our public-IP-pinned HTTP client. No form interaction.
This is a restricted observation window, not a malware detonation environment.
"""
import asyncio
import socket
from urllib.parse import urlsplit
from app.core.fetch import fetch, normalize_url


async def inspect_browser(html, url, channel='msedge', fetcher=fetch):
    from playwright.async_api import async_playwright
    url=normalize_url(url)
    observations=[]
    requests=0
    downloaded=0
    semaphore=asyncio.Semaphore(2)
    blocker=socket.socket()
    blocker.bind(('127.0.0.1',0))  # Reserved but never listening; prevents proxy fallback.
    port=blocker.getsockname()[1]
    try:
        async with async_playwright() as playwright:
            browser=await playwright.chromium.launch(channel=channel or None,headless=True,chromium_sandbox=True,
                proxy={'server':f'http://127.0.0.1:{port}','bypass':'<-loopback>'},
                args=['--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1','--force-webrtc-ip-handling-policy=disable_non_proxied_udp','--disable-background-networking','--disable-quic'])
            try:
                context=await browser.new_context(service_workers='block',accept_downloads=False,permissions=[])
                await context.route_web_socket('**/*',lambda ws:ws.close())
                async def route(handler):
                    nonlocal requests,downloaded
                    request=handler.request
                    parts=urlsplit(request.url)
                    entry={'host':parts.hostname or '', 'path':parts.path[:160], 'method':request.method,'type':request.resource_type,'status':'blocked'}
                    if len(observations)<80:observations.append(entry)
                    if request.url==url and request.resource_type=='document' and requests==0:
                        requests+=1;entry['status']='initial_html'
                        await handler.fulfill(status=200,content_type='text/html',body=html);return
                    if request.method!='GET' or request.resource_type in {'document','media','font','image','websocket'} or requests>=25:
                        await handler.abort();return
                    requests+=1
                    async with semaphore:
                        if downloaded>=10_000_000:
                            await handler.abort();return
                        try:
                            response=await fetcher(request.url,min(2_000_000,10_000_000-downloaded))
                            downloaded+=len(response.body)
                            entry['status']='fetched'
                            await handler.fulfill(status=response.status,content_type=response.mime,body=response.body)
                        except Exception as exc:
                            entry['reason']=type(exc).__name__
                            await handler.abort()
                await context.route('**/*',route)
                page=await context.new_page()
                async def close_extra(other):
                    if other!=page:await other.close()
                context.on('page',close_extra)
                async with asyncio.timeout(25):
                    await page.goto(url,wait_until='domcontentloaded',timeout=15000)
                    await page.wait_for_timeout(1800)
                    rendered=await page.content()
                return {'html':rendered.encode('utf-8')[:2_000_000], 'requests':observations,'downloaded_bytes':downloaded,
                        'limitations':'Restricted initial-load observation only. No logins, form submissions, permissions, downloads, WebSockets or user interactions. Some resource requests are blocked; this changes page behavior. Request presence does not prove data theft.'}
            finally:await browser.close()
    finally:blocker.close()

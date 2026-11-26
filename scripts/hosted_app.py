"""Single-origin hosted entrypoint; frontend and authenticated API share cookies."""
import os
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse
if os.environ.get('RENDER_EXTERNAL_URL'):
    origin = os.environ['RENDER_EXTERNAL_URL'].rstrip('/')
    os.environ['ALLOWED_ORIGINS'] = origin
    os.environ['GOOGLE_REDIRECT_URI'] = origin + '/api/v1/auth/google/callback'

from app.main import app

DIST = Path('/app/frontend/dist')


@app.get('/{requested:path}', include_in_schema=False)
def frontend(requested: str):
    if requested == 'api' or requested.startswith('api/'):
        raise HTTPException(404, 'API route not found')
    target = (DIST / requested).resolve()
    if not target.is_relative_to(DIST.resolve()):
        raise HTTPException(404)
    if target.is_file():
        return FileResponse(target)
    if Path(requested).suffix:
        raise HTTPException(404)
    if os.environ.get('FREE_DEMO') == 'true':
        html = (DIST / 'index.html').read_text()
        notice = '<aside role="note" style="padding:12px;background:#473619;color:#fff;text-align:center;font:14px sans-serif">Free demo: accounts and investigations may reset after restart. Export reports before leaving. AI image/video/audio detectors and antivirus scanning are unavailable. Upload limit: 10 MB.</aside>'
        return HTMLResponse(html.replace('<body>', '<body>' + notice), headers={'Cache-Control': 'no-store'})
    return FileResponse(DIST / 'index.html', headers={'Cache-Control': 'no-cache'})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', '10000')), workers=1, access_log=False)

"""Local capability preflight; --network checks one fixed public page with SSRF guards."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
os.environ.setdefault('CLAMAV_HOST','127.0.0.1')
from app.core.config import settings
from app.services.registry import registry
from app.analyzers.file.antivirus import daemon_status
from app.models.database import Session
from sqlalchemy import text

def check(network=False):
    result={'models':[{k:r.get(k) for k in ('name','version','available','reason')} for r in registry()], 'malware_scanner':daemon_status(settings.clamav_host), 'reputation':'disabled by privacy mode' if settings.privacy_mode else 'configured' if settings.enable_external_reputation and settings.urlhaus_auth_key else 'not configured', 'frontend_build':(ROOT/'frontend/dist/index.html').is_file()}
    try:
        with Session() as db:db.execute(text('SELECT 1'))
        result['database']='available'
    except Exception as exc:result['database']=type(exc).__name__
    if network:
        from app.core.fetch import fetch
        try:
            response=asyncio.run(fetch('https://example.com/'))
            result['public_network']={'available':True,'status':response.status}
        except Exception as exc:result['public_network']={'available':False,'reason':str(exc)[:240],'action':'Start from your normal terminal if a restricted runtime denies outbound connections.'}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--network',action='store_true');args=parser.parse_args()
    print(json.dumps(check(args.network),indent=2))

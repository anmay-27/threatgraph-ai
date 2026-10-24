"""One-command local launcher. Ctrl+C stops only services started by this process."""
import json
import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
children=[]
logs=[]
parser=argparse.ArgumentParser()
parser.add_argument('--browser',action='store_true',help='Enable restricted browser inspection on new URL investigations')
parser.add_argument('--update-signatures',action='store_true',help='Refresh ClamAV databases before starting')
args=parser.parse_args()
environment=os.environ.copy()
if args.browser:environment['ENABLE_BROWSER_INSPECTION']='true'
def listening(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=1):return True
    except OSError:return False
def launch(args,cwd=ROOT,env=None):
    logdir=ROOT/'storage/logs';logdir.mkdir(parents=True,exist_ok=True)
    log=(logdir/f'local-{len(children)}.log').open('a',encoding='utf-8');logs.append(log)
    process=subprocess.Popen(args,cwd=cwd,env=env or environment,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    children.append(process);return process
def wait(port,process,seconds=60):
    for _ in range(seconds):
        if listening(port):return
        if process.poll() is not None:raise RuntimeError(f'Service exited; inspect storage/logs (port {port})')
        time.sleep(1)
    raise RuntimeError(f'Service startup timed out on {port}; inspect storage/logs')

try:
    installation=ROOT/'tools/clamav/install.json'
    if args.update_signatures and installation.exists():
        binary=Path(json.loads(installation.read_text())['bin_dir'])/'freshclam.exe'
        subprocess.run([str(binary),f'--config-file={ROOT / "tools/clamav/freshclam.conf"}','--quiet'],check=True)
    if not listening(3310) and installation.exists():
        binary=Path(json.loads(installation.read_text())['bin_dir'])/'clamd.exe'
        wait(3310,launch([str(binary),f'--config-file={ROOT / "tools/clamav/clamd.conf"}']))
    if not listening(8000):wait(8000,launch([sys.executable,'scripts/dev_api.py']))
    if not (ROOT/'frontend/dist/index.html').exists():raise RuntimeError('Build the frontend first: cd frontend; npm run build')
    if not listening(3000):
        import shutil
        node=shutil.which('node')
        wait(3000,launch([node,'node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','3000'],cwd=ROOT/'frontend'))
    with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=5) as response:
        health=json.load(response)
    print('ThreatGraph: http://localhost:3000',flush=True)
    print('Scanner: '+json.dumps(health.get('malware_scanner')),flush=True)
    print('Keep this terminal open. Ctrl+C stops services this launcher started.',flush=True)
    while True:
        if any(child.poll() is not None for child in children):raise RuntimeError('A service stopped; inspect storage/logs')
        time.sleep(2)
except KeyboardInterrupt:pass
finally:
    for child in reversed(children):
        if child.poll() is None:child.terminate()
    for log in logs:log.close()

"""Send harmless clean data and the standard EICAR test marker over loopback only."""
import json
import socket
import struct
from pathlib import Path

def scan(data):
    with socket.create_connection(('127.0.0.1',3310),timeout=15) as client:
        client.sendall(b'zINSTREAM\0'+struct.pack('!I',len(data))+data+struct.pack('!I',0))
        return client.recv(4096).decode().strip('\0\n')

clean=scan(b'ThreatGraph clean scanner connectivity fixture.')
marker=b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$'+b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
test=scan(marker)
result={'clean':clean,'eicar_test':test,'passed':clean.endswith('OK') and test.endswith('FOUND'),'note':'Harmless standard test marker, never written as an uploaded file.'}
Path('research/results/scanner_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
if not result['passed']:raise SystemExit(1)

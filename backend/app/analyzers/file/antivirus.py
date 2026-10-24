"""Stream to an operator-configured LOCAL ClamAV daemon without writing there."""

import socket
import struct
import time
from pathlib import Path


def daemon_status(host: str) -> dict:
    if not host:
        return {'available': False, 'reason': 'Local scanner is not configured'}
    try:
        with socket.create_connection((host,3310),timeout=2) as client:
            client.sendall(b'zVERSION\0')
            version=client.recv(4096).decode('utf-8',errors='replace').strip('\0\n')
        if not version.startswith('ClamAV '): raise ValueError('Unexpected scanner response')
        return {'available':True,'version':version,'scope':'Downloaded/uploaded bytes; signature scanning does not establish URL safety'}
    except (OSError,ValueError) as exc:
        return {'available':False,'reason':f'Local scanner is unreachable or not ready ({type(exc).__name__})'}


def scan_daemon(path: Path, host: str) -> tuple[bool, str]:
    deadline = time.monotonic() + 30
    with socket.create_connection((host, 3310), timeout=5) as client:
        client.sendall(b"zINSTREAM\0")
        with path.open("rb") as file:
            while block := file.read(65536):
                if time.monotonic() > deadline:
                    raise TimeoutError("ClamAV scan exceeded deadline")
                client.sendall(struct.pack("!I", len(block)) + block)
        client.sendall(struct.pack("!I", 0))
        reply = bytearray()
        while len(reply) < 4096:
            block = client.recv(1024)
            if not block:
                break
            reply.extend(block)
            if b"\0" in block:
                break
    text = bytes(reply).decode("utf-8", errors="replace").strip("\0\n")
    if text.endswith("FOUND"):
        return True, text
    if text.endswith("OK"):
        return False, text
    raise ValueError("ClamAV unavailable: " + text[:200])

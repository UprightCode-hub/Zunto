#server/core/file_scanning.py
import os
import socket
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass
class MalwareScanResult:
    is_clean: bool
    reason: str = ''


class MalwareScannerUnavailable(Exception):
    pass


def _clamav_scan_file(uploaded_file) -> MalwareScanResult:
    host = getattr(settings, 'MALWARE_SCAN_CLAMAV_HOST', '127.0.0.1')
    port = int(getattr(settings, 'MALWARE_SCAN_CLAMAV_PORT', 3310))
    timeout = int(getattr(settings, 'MALWARE_SCAN_TIMEOUT_SECONDS', 5))

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(b'zINSTREAM\0')

            if hasattr(uploaded_file, 'chunks'):
                chunks = uploaded_file.chunks()
            else:
                chunks = [uploaded_file.read()]

            for chunk in chunks:
                if not chunk:
                    continue
                sock.sendall(len(chunk).to_bytes(4, byteorder='big'))
                sock.sendall(chunk)

            sock.sendall((0).to_bytes(4, byteorder='big'))

            response_bytes = b''
            while True:
                packet = sock.recv(1024)
                if not packet:
                    break
                response_bytes += packet
                if b'\n' in packet:
                    break

            response = response_bytes.decode('utf-8', errors='replace').strip()
            if 'FOUND' in response:
                return MalwareScanResult(is_clean=False, reason=response)
            if 'OK' in response:
                return MalwareScanResult(is_clean=True)
            return MalwareScanResult(is_clean=False, reason='unexpected-clamav-response')
    except OSError as exc:
        raise MalwareScannerUnavailable('clamav-unreachable') from exc
    finally:
        uploaded_file.seek(0)


def scan_uploaded_file(uploaded_file) -> MalwareScanResult:
    if not getattr(settings, 'MALWARE_SCAN_ENABLED', False):
        return MalwareScanResult(is_clean=True)

    scanner = getattr(settings, 'MALWARE_SCAN_BACKEND', 'clamav').lower()

    if scanner == 'clamav':
        return _clamav_scan_file(uploaded_file)

    raise MalwareScannerUnavailable('unsupported-malware-scan-backend')


def quarantine_uploaded_file(uploaded_file, *, reason: str) -> str:
    quarantine_dir = Path(getattr(settings, 'MALWARE_QUARANTINE_DIR', settings.MEDIA_ROOT + '/quarantine'))
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    original_name = Path(getattr(uploaded_file, 'name', 'upload.bin')).name
    token = uuid.uuid4().hex
    destination = quarantine_dir / f'{token}-{original_name}'
    metadata_path = quarantine_dir / f'{token}.meta'

    with destination.open('wb') as out_file:
        for chunk in uploaded_file.chunks() if hasattr(uploaded_file, 'chunks') else [uploaded_file.read()]:
            out_file.write(chunk)
    uploaded_file.seek(0)

    metadata_path.write_text(
        f'reason={reason}{os.linesep}original_name={original_name}{os.linesep}',
        encoding='utf-8',
    )

    return str(destination)

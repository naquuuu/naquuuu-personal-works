"""Authenticated warm opencode relay, safe output, optional trusted context reuse."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from relay_outbound import requested_creative_allowance, sanitize_relay_events


def warm_server_available() -> bool:
    """Choose a route BEFORE execution; a failed invocation is never replayed."""
    try:
        with socket.create_connection(('127.0.0.1', 4096), timeout=1):
            return True
    except OSError:
        return False


def opencode_binary() -> str:
    configured = os.environ.get('NAQUUUU_OPENCODE_BIN')
    if configured:
        return configured
    installed = Path.home() / '.opencode/bin/opencode'
    if installed.is_file():
        return str(installed)
    return shutil.which('opencode') or str(installed)


def relay_timeout() -> int:
    """Client-side wait budget. Default stays at the previous 120s floor."""
    try:
        value = int(os.environ.get('NAQUUUU_RELAY_TIMEOUT', ''))
    except ValueError:
        return 120
    return value if value > 0 else 120


def image_attachment(value: str) -> str:
    """Only regular image files inside host-controlled attachment cache roots."""
    hermes = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    configured = os.environ.get('NAQUUUU_RELAY_ATTACHMENT_ROOT')
    roots = [Path(configured)] if configured else [hermes / 'cache/images', hermes / 'image_cache']
    path = Path(value).resolve(strict=True)
    if not any(path.is_relative_to(root.resolve()) for root in roots):
        raise ValueError('Attachment outside cache')
    if not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Attachment is not a bounded regular file')
    if path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}:
        raise ValueError('Unsupported attachment type')
    # A renamed credential/text file must never be passed to a model as an image.
    with path.open('rb') as stream:
        header = stream.read(16)
    signatures = {
        '.png': header.startswith(b'\x89PNG\r\n\x1a\n'),
        '.jpg': header.startswith(b'\xff\xd8\xff'),
        '.jpeg': header.startswith(b'\xff\xd8\xff'),
        '.gif': header[:6] in {b'GIF87a', b'GIF89a'},
        '.webp': header[:4] == b'RIFF' and header[8:12] == b'WEBP',
        '.bmp': header.startswith(b'BM'),
    }
    if not signatures[path.suffix.lower()]:
        raise ValueError('Attachment is not an image')
    return str(path)


def server_env() -> dict:
    env = os.environ.copy()
    try:
        pid = subprocess.check_output(['systemctl', '--user', 'show', 'opencode-serve.service', '-p', 'MainPID', '--value'], text=True).strip()
        for entry in Path('/proc', pid, 'environ').read_bytes().split(b'\0'):
            if entry.startswith((b'OPENCODE_SERVER_PASSWORD=', b'OPENCODE_SERVER_USERNAME=')):
                key, value = entry.decode().split('=', 1)
                env[key] = value
    except (OSError, subprocess.SubprocessError):
        pass
    return env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('task', nargs='?')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--file', action='append', default=[])
    args = parser.parse_args()
    root_value = os.environ.get('NAQUUUU_WORKSPACE')
    if not root_value:
        print('Workspace belum tersedia sekarang.')
        return 1
    root = Path(root_value)
    if args.status:
        try:
            print((root / 'internal-docs/STATUS.md').read_text(encoding='utf-8'))
            return 0
        except OSError:
            print('Status workspace belum tersedia sekarang.')
            return 1
    if not args.task:
        parser.error('task required')
    # args.task is the current request passed to this invocation. Grant only
    # explicitly requested, bounded art/repetition; output claims cannot grant it.
    repetition_allowance = requested_creative_allowance(args.task)
    binary = opencode_binary()
    env = server_env()
    cache = Path.home() / '.local/state/naquuuu/relay-sessions'
    # Only a host-injected context enables reuse. Never use a global last session.
    context = env.get('NAQUUUU_RELAY_CONTEXT')
    path = cache / (hashlib.sha256(context.encode()).hexdigest() + '.json') if context else None
    session = None
    if path and path.exists():
        try:
            cached = json.loads(path.read_text(encoding='utf-8'))
            session = cached.get('session') if isinstance(cached, dict) else None
            if not isinstance(session, str):
                session = None
        except (OSError, ValueError):
            session = None
    base = [binary, 'run', '--format', 'json']
    try:
        files = [item for f in args.file for item in ['--file', image_attachment(f)]]
    except (OSError, RuntimeError, ValueError):
        print('Lampirannya belum bisa dibuka sekarang.')
        return 1
    # A reachability failure has no task side effects. Once opencode is invoked,
    # empty stdout, a broken connection or nonzero exit cannot prove rejection.
    attached = warm_server_available()
    command = (base + (['--attach', 'http://127.0.0.1:4096', '--dir', str(root)]
                      + (['--session', session] if session else []) if attached else [])
               + files + [args.task])
    try:
        result = subprocess.run(command, cwd=root, env=env, text=True,
                                encoding='utf-8', errors='replace',
                                capture_output=True, timeout=relay_timeout())
    except subprocess.TimeoutExpired:
        print('Batas waktu tercapai; hasilnya belum pasti, jadi tugas tidak diulang.')
        return 1
    except OSError:
        print('Tugasnya belum bisa dijalankan sekarang.')
        return 1
    events = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            pass
    if result.returncode != 0 or any(e.get('type') == 'error' for e in events):
        print('Hasil tugas belum pasti; tugas tidak diulang otomatis.')
        return 1
    reply, is_clean = sanitize_relay_events(events, repetition_allowance=repetition_allowance)
    if not reply:
        print('Jawaban akhir belum tersedia; tugas tidak diulang otomatis.')
        return 1
    if path and events and is_clean:
        sid = next((e.get('sessionID') for e in reversed(events) if isinstance(e.get('sessionID'), str)), None)
        if sid:
            temp = None
            try:
                cache.mkdir(parents=True, exist_ok=True, mode=0o700)
                fd, temp = tempfile.mkstemp(dir=cache)
                with os.fdopen(fd, 'w', encoding='utf-8') as out:
                    json.dump({'session': sid}, out)
                os.replace(temp, path)
            except OSError:
                pass  # Completed work must not become a retry because caching failed.
            finally:
                if temp and os.path.exists(temp):
                    os.unlink(temp)
    print(reply)
    return 0

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())

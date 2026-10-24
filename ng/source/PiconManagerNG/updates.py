# SPDX-License-Identifier: GPL-3.0-or-later
"""Staged, verified PNG replacement with mandatory backups."""
import hashlib
import json
import os
import re
import shutil
import struct
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from .core import VALID_SRP

MAX_PNG = 2 * 1024 * 1024
TRUSTED_HOSTS = {'raw.githubusercontent.com'}

def verify_png(blob, expected_dimensions=(400, 240)):
    if len(blob) < 45 or len(blob) > MAX_PNG or not blob.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Invalid PNG')
    offset, seen_ihdr, seen_idat, seen_iend = 8, False, False, False
    while offset < len(blob):
        if offset + 12 > len(blob):
            raise ValueError('Truncated PNG')
        size = struct.unpack('>I', blob[offset:offset+4])[0]
        end = offset + 12 + size
        if end > len(blob):
            raise ValueError('Bad PNG chunk size')
        kind = blob[offset+4:offset+8]
        payload = blob[offset+8:offset+8+size]
        stored_crc = struct.unpack('>I', blob[end-4:end])[0]
        if (zlib.crc32(kind+payload) & 0xffffffff) != stored_crc:
            raise ValueError('Bad PNG CRC')
        if not seen_ihdr:
            if kind != b'IHDR' or size != 13:
                raise ValueError('Missing PNG IHDR')
            w, h = struct.unpack('>II', payload[:8])
            if (w, h) != tuple(expected_dimensions):
                raise ValueError('Unexpected picon dimensions: %s x %s' % (w, h))
            seen_ihdr = True
        if kind == b'IDAT':
            seen_idat = True
        if kind == b'IEND':
            seen_iend = True
            if size or end != len(blob):
                raise ValueError('Trailing PNG data')
            break
        offset = end
    if not (seen_ihdr and seen_idat and seen_iend):
        raise ValueError('Incomplete PNG')

def validate_manifest(doc, style_id):
    if doc.get('schema') != 1 or doc.get('style_id') != style_id:
        raise ValueError('Manifest schema/style mismatch; no changes allowed')
    items = doc.get('items')
    if not isinstance(items, dict):
        raise ValueError('Missing items')
    for name, meta in items.items():
        if not VALID_SRP.fullmatch(name) or not isinstance(meta, dict):
            raise ValueError('Unsafe picon name')
        if not re.fullmatch(r'[0-9a-f]{64}', meta.get('sha256', '')):
            raise ValueError('Missing SHA256')
        url = urlparse(meta.get('url', ''))
        if (url.scheme != 'https' or url.hostname not in TRUSTED_HOSTS
                or not url.path.startswith('/wacayoub/PiconManager-Pro/')):
            raise ValueError('Disallowed picon source')
    return items

def plan_replacements(services, picon_dir, manifest, style_id, overwrite=True):
    """Planning is read-only."""
    items = validate_manifest(manifest, style_id)
    root = Path(picon_dir)
    names = {s['picon'] for s in services if s.get('picon')}
    plan = []
    for name in sorted(names & items.keys()):
        target = root / name
        if target.is_file():
            if not overwrite:
                continue
            with target.open('rb') as f:
                digest = hashlib.file_digest(f, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(f.read()).hexdigest()
            if digest == items[name]['sha256']:
                continue
        plan.append({'name':name,'url':items[name]['url'],
                     'sha256':items[name]['sha256'],
                     'action':'replace' if target.exists() else 'new'})
    return plan

def fetch_blob(url, timeout=12):
    req = Request(url, headers={'User-Agent':'PiconManagerNG/2.0'})
    with urlopen(req, timeout=timeout) as resp:
        if urlparse(resp.geturl()).hostname not in TRUSTED_HOSTS:
            raise ValueError('Unsafe redirect')
        data = resp.read(MAX_PNG + 1)
    if len(data) > MAX_PNG:
        raise ValueError('PNG too large')
    return data

def apply_plan(plan, picon_dir, backup_root, fetch=fetch_blob,
               expected_dimensions=(400, 240)):
    """Stage entire batch, verify and back up before committing; rollback on error."""
    root, backups = Path(picon_dir), Path(backup_root)
    root.mkdir(parents=True, exist_ok=True)
    batch = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = backups / batch
    staged, applied = [], []
    try:
        for entry in plan:
            name = entry['name']
            if not VALID_SRP.fullmatch(name):
                raise ValueError('Unsafe picon filename')
            url = entry['url']
            u = urlparse(url)
            if u.scheme != 'https' or u.hostname not in TRUSTED_HOSTS or not u.path.startswith('/wacayoub/PiconManager-Pro/'):
                raise ValueError('Unsafe URL')
            data = fetch(url)
            verify_png(data, expected_dimensions)
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('SHA256 mismatch for %s' % name)
            fd, path = tempfile.mkstemp(prefix='.ng-', suffix='.png', dir=str(root))
            with os.fdopen(fd,'wb') as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            staged.append((name,Path(path)))
        backup.mkdir(parents=True, exist_ok=False)
        for name, _ in staged:
            target = root / name
            if target.is_symlink():
                raise ValueError('Symlink target rejected')
            if target.is_file():
                shutil.copy2(str(target),str(backup / name))
        for name, staged_path in staged:
            os.replace(str(staged_path),str(root/name))
            applied.append(name)
        (backup/'transaction.json').write_text(
            json.dumps({'applied':applied,'date':batch},indent=2),encoding='utf-8')
        return {'updated':len(applied),'backup':str(backup)}
    except Exception:
        for name in reversed(applied):
            original, target = backup/name, root/name
            if original.is_file():
                shutil.copy2(str(original),str(target))
            elif target.exists():
                target.unlink()
        raise
    finally:
        for _, path in staged:
            if path.exists(): path.unlink()

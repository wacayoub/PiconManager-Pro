# SPDX-License-Identifier: GPL-3.0-or-later
"""Enigma2 bouquet/picon scanner. Python 3; no Enigma2 dependencies."""
from __future__ import annotations
import re
from pathlib import Path

VALID_SRP = re.compile(r'^[0-9A-Fa-f]+(?:_[0-9A-Fa-f]+){9}\.png$')

def picon_name(service_ref):
    """Full Enigma2 service-ref picon filename (10 fields)."""
    parts = service_ref.split(':', 10)
    if len(parts) < 10:
        return None
    head = parts[:10]
    if not all(re.fullmatch('[0-9A-Fa-f]+', x or '') for x in head):
        return None
    if int(head[1], 16) in (4, 7, 64):
        return None
    if all(int(x, 16) == 0 for x in head[3:7]):
        return None
    return '_'.join(x.upper() for x in head) + '.png'

def srp_key(service_ref):
    """picons/picons key (SID_TSID_ONID_NAMESPACE)."""
    head = service_ref.split(':', 10)
    if picon_name(service_ref) is None:
        return None
    return '_'.join(x.upper() for x in head[3:7])

def scan_bouquet_files(directory, include_radio=True):
    directory = Path(directory)
    files = sorted(directory.glob('userbouquet.*.tv'))
    if include_radio:
        files += sorted(directory.glob('userbouquet.*.radio'))
    out, seen = [], set()
    for path in files:
        try:
            lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        except OSError:
            continue
        entry = None
        def flush():
            if entry is not None and entry['ref'] not in seen:
                seen.add(entry['ref'])
                out.append(entry.copy())
        for line in lines:
            if line.startswith('#SERVICE '):
                flush()
                ref = line[len('#SERVICE '):].strip()
                fname = picon_name(ref)
                if ref.startswith(('1:7:', '1:64:', '1:4:')):
                    entry = None
                else:
                    entry = {'ref': ref, 'name': '', 'picon': fname,
                             'srp_key': srp_key(ref), 'bouquet': path.name}
            elif line.startswith('#DESCRIPTION ') and entry is not None:
                entry['name'] = line[len('#DESCRIPTION '):].strip()
        flush()
    return out

def find_installed(services, picon_dir):
    root = Path(picon_dir)
    result = {'total': len(services), 'found': 0,
              'missing': 0, 'unsupported': 0}
    for item in services:
        name = item['picon']
        if not name or not VALID_SRP.fullmatch(name):
            result['unsupported'] += 1
        elif (root / name).is_file():
            result['found'] += 1
        else:
            result['missing'] += 1
    return result

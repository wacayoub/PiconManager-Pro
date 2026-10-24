# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only Enigma2 inventory and conservative service identification."""
import re
import hashlib
import os
import unicodedata
from pathlib import Path
from urllib.parse import unquote

VALID_SRP = re.compile(r'^[0-9A-Fa-f]+(?:_[0-9A-Fa-f]+){9}\.png$')
INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
HEX = re.compile(r'^[0-9a-fA-F]+$')


def clean_name(name):
    return unicodedata.normalize('NFC', name.replace('\x80', '').replace('\x86', '').replace('\x87', '')).strip()


def utf8_name(name):
    return INVALID_NAME.sub('_', clean_name(name)).rstrip('. ').lower()


def valid_filename(name):
    return (isinstance(name, str) and name.endswith('.png') and
            name not in ('.png', '..png') and not name.startswith('.') and
            len(name.encode('utf-8')) <= 240 and not INVALID_NAME.search(name))


def ref_fields(ref):
    parts = ref.split(':', 10)
    if len(parts) < 10 or not all(HEX.fullmatch(x or '') for x in parts[:10]):
        return None
    # Enigma2 flags are hexadecimal; stream reference types are decimal.
    if int(parts[1], 16) & (1 | 2 | 4 | 64 | 128):
        return None
    return parts[:10]


def service_kind(ref):
    fields = ref_fields(ref)
    if fields is None:
        return 'unsupported'
    return _kind(fields, ref)


def _kind(fields, ref):
    tail = unquote(ref.split(':', 10)[10] if ref.count(':') >= 10 else '')
    if fields[0] != '1' or re.match(r'(?i)^(?:https?|rtsp|rtmp|udp|rtp|srt)://', tail):
        return 'IPTV'
    ns = int(fields[6], 16) >> 16
    return 'DTT' if ns == 0xEEEE else 'CABLE' if ns == 0xFFFF else 'SAT'


def picon_name(service_ref):
    fields = ref_fields(service_ref)
    if fields is None or not any(int(x, 16) for x in fields[3:7]):
        return None
    return '_'.join(x.upper() for x in fields) + '.png'


def srp_key(service_ref):
    fields = ref_fields(service_ref)
    if picon_name(service_ref) is None:
        return None
    if service_kind(service_ref) == 'IPTV' and int(fields[6], 16) == 0:
        return None  # private IPTV ids must never masquerade as DVB identifiers
    return '_'.join('%X' % int(x, 16) for x in fields[3:7])


def picon_candidates(service_ref, name=''):
    """OpenATV lookup order: exact, namespace, stream/type fallback, UTF8/SNP."""
    fields = ref_fields(service_ref)
    if fields is None:
        return []
    out = []
    def add(parts):
        value = '_'.join(parts) + '.png'
        if value not in out:
            out.append(value)
    if any(int(x, 16) for x in fields[3:7]):
        add([x.upper() for x in fields])
        fields = [('%X' % int(x, 16)) if i else x for i, x in enumerate(fields)]
        add(fields)
        if int(fields[6], 16) & 0xFFFF:
            fields[6] = '%X' % (int(fields[6], 16) & 0xFFFF0000)
            add(fields)
        if fields[0] != '1':
            fields[0] = '1'
            add(fields)
        if fields[2] != '1':
            fields[2] = '1'
            add(fields)
    snp = utf8_name(name)
    legacy = re.sub('[^a-z0-9]', '', snp.replace('&', 'and').replace('+', 'plus').replace('*', 'star'))
    for value in (snp, legacy, re.sub(r'(fhd|uhd|hd|sd|4k)$', '', snp).strip(),
                  re.sub(r'(fhd|uhd|hd|sd|4k)$', '', legacy).strip()):
        if value and valid_filename(value + '.png') and value + '.png' not in out:
            out.append(value + '.png')
    return out


def _lamedb_names(directory):
    names = {}
    path = directory / 'lamedb'
    if path.is_file():
        with path.open(encoding='utf8', errors='replace') as stream:
            for line in stream:
                if line.strip() == 'services':
                    break
            for line in stream:
                if line.strip() == 'end':
                    break
                parts = line.strip().split(':')
                if len(parts) >= 5 and all(HEX.fullmatch(x) for x in parts[:5]):
                    name = next(stream, '').strip()
                    next(stream, '')
                    sid, ns, tsid, onid = (int(x, 16) for x in parts[:4])
                    names[(sid, tsid, onid, ns)] = clean_name(name)
    path = directory / 'lamedb5'
    if path.is_file():
        with path.open(encoding='utf8', errors='replace') as stream:
            for line in stream:
                match = re.match(r's:([^,]+),"((?:[^"\\]|\\.)*)"', line)
                if match:
                    parts = match[1].split(':')
                    if len(parts) >= 4 and all(HEX.fullmatch(x) for x in parts[:4]):
                        sid, ns, tsid, onid = (int(x, 16) for x in parts[:4])
                        names[(sid, tsid, onid, ns)] = clean_name(match[2].replace('\\"', '"'))
    return names


def _bouquet_paths(directory, include_radio):
    directory = directory.resolve()
    roots = [directory / 'bouquets.tv']
    if include_radio:
        roots.append(directory / 'bouquets.radio')
    roots = [p for p in roots if p.is_file()]
    if not roots:
        roots = sorted(directory.glob('userbouquet.*.tv'))
        if include_radio:
            roots += sorted(directory.glob('userbouquet.*.radio'))
    seen, ordered = set(), []
    def visit(path):
        if path.name in seen or path.parent != directory or not path.is_file():
            return
        seen.add(path.name)
        ordered.append(path)
        with path.open(encoding='utf8', errors='replace') as stream:
            for line in stream:
                match = re.search(r'FROM BOUQUET "([^"/\\]+)"', line) if 'FROM BOUQUET' in line else None
                if match and (include_radio or not match[1].endswith('.radio')):
                    visit(directory / match[1])
    for root in roots:
        visit(root)
    return ordered


def scan_bouquet_files(directory, include_radio=True, progress=None):
    directory = Path(directory)
    names = _lamedb_names(directory)
    out, seen = [], set()
    paths = _bouquet_paths(directory, include_radio)
    for position, path in enumerate(paths):
        if progress and position % 8 == 0:
            progress('Analyse : %d/%d bouquets • %d chaînes' % (position, len(paths), len(out)))
        entry = None
        def flush():
            identity = hashlib.sha256(entry['ref'].encode()).hexdigest() if entry else None
            if entry is not None and identity not in seen:
                fields = entry.pop('_fields')
                key = tuple(int(x, 16) for x in fields[3:7])
                entry['name'] = clean_name(entry['name']) or names.get(key, '')
                if not entry['name']:
                    tail = entry['ref'].split(':', 10)
                    if len(tail) == 11 and ':' in tail[10]:
                        entry['name'] = clean_name(unquote(tail[10].rsplit(':', 1)[-1]))
                if entry['picon'] is None and entry['name']:
                    snp = utf8_name(entry['name']) + '.png'
                    entry['picon'] = snp if valid_filename(snp) else None
                seen.add(identity)
                entry['identity'] = identity
                # Only the header is needed after parsing. Do not retain IPTV credentials.
                entry['ref'] = ':'.join(fields) + ':'
                out.append(entry.copy())
        with path.open(encoding='utf8', errors='replace') as stream:
            for line in stream:
                if line.startswith('#SERVICE '):
                    flush()
                    ref = line[9:].strip()
                    fields = ref_fields(ref)
                    kind = _kind(fields, ref) if fields is not None else None
                    has_ids = fields is not None and any(int(x, 16) for x in fields[3:7])
                    entry = None if fields is None else {
                        'ref': ref, '_fields': fields, 'name': '',
                        'picon': '_'.join(x.upper() for x in fields) + '.png' if has_ids else None,
                        'srp_key': '_'.join('%X' % int(x, 16) for x in fields[3:7]) if has_ids and (kind != 'IPTV' or int(fields[6], 16)) else None,
                        'kind': kind,
                        'radio': path.suffix == '.radio' or int(fields[2], 16) in (2, 10),
                        'bouquet': path.name}
                elif line.startswith('#DESCRIPTION ') and entry is not None:
                    entry['name'] = line[13:].strip()
        flush()
    return out


def annotate_installed(services, picon_dirs):
    """Stat only relevant files, without enumerating the whole installed pack."""
    if isinstance(picon_dirs, (str, Path)):
        picon_dirs = [picon_dirs]
    roots = [Path(p) for p in picon_dirs]
    indexes = {}
    if len(services) > 2000:
        for root in roots:
            try:
                with os.scandir(root) as entries:
                    indexes[root] = {e.name for e in entries if e.name.endswith('.png')}
            except OSError:
                indexes[root] = set()
    for item in services:
        item['installed'] = None
        candidates = (item.get('candidates') or picon_candidates(item['ref'], item.get('name', ''))) if item.get('ref') else [item.get('picon')]
        for root in roots:
            found = next((root / n for n in candidates
                          if n and valid_filename(n) and (n in indexes[root] if root in indexes else (root / n).is_file())), None)
            if found:
                item['installed'] = str(found)
                break
    return services


def find_installed(services, picon_dir):
    annotate_installed(services, picon_dir)
    result = {'total': len(services), 'found': 0, 'missing': 0, 'unsupported': 0}
    for item in services:
        result['found' if item['installed'] else 'missing' if item.get('picon') else 'unsupported'] += 1
    return result

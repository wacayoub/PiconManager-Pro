# SPDX-License-Identifier: GPL-3.0-or-later
"""Selective picons/picons index, exact/alias/UTF8 matching without guesses."""
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path
from .core import srp_key, utf8_name
from .network import open_source, read_json
from .storage import atomic_json

API = 'https://api.github.com/repos/picons/picons'
RAW = 'https://raw.githubusercontent.com/picons/picons/'
LOGO_ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._+\-]{0,199}$')


def name_key(value):
    value = value.replace('+', 'plus').replace('&', 'and').replace('*', 'star')
    return ''.join(c for c in unicodedata.normalize('NFC', value).casefold() if c.isalnum())


def alias_key(service):
    # Never persist provider URLs/credentials in mapping files or diagnostic logs.
    return service.get('identity') or hashlib.sha256(service['ref'].encode('utf8')).hexdigest()


def _wanted(services):
    srps, names = set(), set()
    for service in services:
        key = service.get('srp_key')
        if key:
            srps.add(key)
        if service.get('name'):
            names.add(name_key(utf8_name(service['name'])))
    return srps, names


def read_index_lines(lines, wanted, key_fn=lambda x: x):
    found = {}
    for raw in lines:
        if isinstance(raw, bytes):
            raw = raw.decode('utf8', 'replace')
        left, sep, right = raw.strip().partition('=')
        if not sep or not LOGO_ID.fullmatch(right):
            continue
        key = key_fn(left)
        if key in wanted:
            found.setdefault(key, set()).add(right)
    return {key: sorted(values) for key, values in found.items()}


def _stream_index(url, wanted, key_fn):
    with open_source(url) as response:
        def bounded_lines():
            size = 0
            while True:
                line = response.readline(8193)
                if not line:
                    break
                size += len(line)
                if len(line) > 8192 or size > 12 * 1024 * 1024:
                    raise ValueError('Index GitHub trop volumineux')
                yield line
        return read_index_lines(bounded_lines(), wanted, key_fn)


def load_catalog(services, cache_dir, force=False):
    srps, names = _wanted(services)
    fingerprint = hashlib.sha256(json.dumps([sorted(srps), sorted(names)]).encode()).hexdigest()
    cache = Path(cache_dir) / 'catalog.json'
    if not force and cache.is_file():
        try:
            doc = json.loads(cache.read_text(encoding='utf8'))
            if doc.get('fingerprint') == fingerprint and time.time() - doc.get('fetched_at', 0) < 86400:
                return doc
        except (OSError, ValueError):
            pass
    commit = read_json(API + '/commits/master', 512 * 1024)['sha']
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Révision GitHub invalide')
    doc = {'schema': 1, 'commit': commit, 'fingerprint': fingerprint, 'fetched_at': time.time(),
           'srp': _stream_index(RAW + commit + '/build-source/srp.index', srps, lambda x: x.upper()),
           'names': _stream_index(RAW + commit + '/build-source/utf8snp.index', names, name_key)}
    atomic_json(cache, doc)
    return doc


def match_service(service, catalog, aliases=None):
    exact = catalog.get('srp', {}).get(service.get('srp_key'), [])
    if len(exact) == 1:
        return {'logo': exact[0], 'method': 'SRP exact', 'candidates': exact}
    alias = (aliases or {}).get(alias_key(service))
    # Alias is a user-verified catalogue ID, scoped to this full service identity.
    if alias and LOGO_ID.fullmatch(alias):
        return {'logo': alias, 'method': 'Choix vérifié', 'candidates': [alias]}
    names = catalog.get('names', {}).get(name_key(utf8_name(service.get('name', ''))), [])
    candidates = sorted(set(exact + names))
    if len(candidates) == 1:
        return {'logo': candidates[0], 'method': 'Nom UTF8', 'candidates': candidates}
    return {'logo': None, 'method': 'Ambigu' if candidates else 'Sans correspondance', 'candidates': candidates}


def materialize_manifest(manifest, services):
    """Public catalogue is by logo ID; receiver-specific references stay local."""
    logos = manifest.get('logos', {})
    items = dict(manifest.get('items', {}))
    conflicts = set()
    for service in services:
        logo = service.get('match', {}).get('logo')
        name = service.get('picon')
        if name and logo in logos:
            if name in items and items[name] != logos[logo]:
                conflicts.add(name)
            else:
                items[name] = logos[logo]
    for name in conflicts:
        items.pop(name, None)  # different IPTV channels sharing a private ref require manual handling
    return dict(manifest, items=items)

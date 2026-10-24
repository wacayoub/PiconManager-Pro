# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified selective updates, preview staging and durable undo/recovery."""
import hashlib
import io
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from .core import valid_filename
from .storage import atomic_bytes, atomic_json, digest, directory_lock, sync_dir

MAX_PNG = 2 * 1024 * 1024
TRUSTED_HOSTS = {'raw.githubusercontent.com'}
SHA = re.compile(r'^[0-9a-f]{64}$')


def check_url(value):
    u = urlparse(value)
    path = unquote(u.path)
    if (u.scheme != 'https' or u.netloc != 'raw.githubusercontent.com' or
            not path.startswith('/wacayoub/PiconManager-Pro/') or
            any(p in ('.', '..') for p in path.split('/')) or u.query or u.fragment or
            any(ord(c) < 32 for c in value)):
        raise ValueError('Source de mise à jour non autorisée')
    return value


def verify_png(blob, expected_dimensions=(400, 240)):
    if len(blob) > MAX_PNG or not blob.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('PNG invalide')
    from PIL import Image
    try:
        with Image.open(io.BytesIO(blob)) as image:
            if image.size != tuple(expected_dimensions) or image.format != 'PNG':
                raise ValueError('Dimensions ou format du picon incorrects')
            image.verify()
        with Image.open(io.BytesIO(blob)) as image:
            image.load()  # catches a valid CRC around corrupt/short compressed pixels
            if getattr(image, 'n_frames', 1) != 1:
                raise ValueError('PNG animé refusé')
    except (OSError, SyntaxError) as exc:
        raise ValueError('PNG endommagé') from exc


def validate_manifest(doc, style_id):
    if not isinstance(doc, dict) or doc.get('schema') not in (1, 2) or not style_id or doc.get('style_id') != style_id:
        raise ValueError('Profil visuel du catalogue différent : aucun remplacement permis')
    items = doc.get('items')
    if not isinstance(items, dict) or len(items) > 100000:
        raise ValueError('Catalogue invalide')
    for name, meta in items.items():
        if not valid_filename(name) or not isinstance(meta, dict):
            raise ValueError('Nom de picon invalide')
        if not SHA.fullmatch(meta.get('sha256', '')):
            raise ValueError('SHA256 manquant')
        check_url(meta.get('url', ''))
    return items


def plan_replacements(services, picon_dir, manifest, style_id, overwrite=True):
    items = validate_manifest(manifest, style_id)
    root = Path(picon_dir)
    names = {s['picon'] for s in services if s.get('picon')}
    plan = []
    for name in sorted(names & items.keys()):
        target = root / name
        old_sha = digest(target)
        if old_sha is not None and (not overwrite or old_sha == items[name]['sha256']):
            continue
        plan.append({'name': name, 'url': items[name]['url'], 'sha256': items[name]['sha256'],
                     'size': items[name].get('size', MAX_PNG),
                     'old_sha256': old_sha, 'action': 'replace' if old_sha else 'new'})
    return plan


def fetch_blob(url, timeout=12):
    check_url(url)
    with urlopen(Request(url, headers={'User-Agent': 'PiconManagerNG/2.0'}), timeout=timeout) as resp:
        check_url(resp.geturl())
        data = resp.read(MAX_PNG + 1)
    if len(data) > MAX_PNG:
        raise ValueError('PNG trop volumineux')
    return data


def _journal(batch):
    doc = json.loads((batch / 'transaction.json').read_text(encoding='utf8'))
    if doc.get('schema') != 2 or not isinstance(doc.get('entries'), list):
        raise ValueError('Sauvegarde incompatible')
    names = set()
    for entry in doc['entries']:
        name = entry.get('name')
        if not valid_filename(name) or name in names or not SHA.fullmatch(entry.get('sha256', '')):
            raise ValueError('Sauvegarde invalide')
        old = entry.get('old_sha256')
        if old is not None and not SHA.fullmatch(old):
            raise ValueError('Empreinte de sauvegarde invalide')
        names.add(name)
    return doc


def _verified_cached(path, sha256, dimensions):
    try:
        if path.is_symlink() or path.stat().st_size > MAX_PNG:
            return None
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != sha256:
            return None
        verify_png(data, dimensions)
        return data
    except (OSError, ValueError):
        return None


def stage_plan(plan, picon_dir, backup_root, fetch=fetch_blob, expected_dimensions=(400, 240), cache_dir=None):
    """Reuse verified local PNGs before downloading selected changes."""
    root = Path(picon_dir).resolve()
    backups = Path(backup_root)
    previous = list_backups(backups)
    for pending in previous:
        if pending['state'] in ('applying', 'restoring') and Path(pending['root']).resolve() == root:
            raise ValueError('Une opération interrompue doit être restaurée depuis Sauvegardes avant une nouvelle mise à jour.')
    batch = backups / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:12])
    if not plan:
        raise ValueError('Aucun picon sélectionné')
    if len({p['name'] for p in plan}) != len(plan):
        raise ValueError('Picons en double')
    required = MAX_PNG + sum(2 * (p['size'] if isinstance(p.get('size'), int) and 0 < p['size'] <= MAX_PNG else MAX_PNG)
                            + ((root / p['name']).stat().st_size if valid_filename(p['name']) and (root / p['name']).is_file() else 0)
                            for p in plan)
    backups.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(backups).free < required:
        raise OSError('Espace insuffisant pour téléchargement et sauvegarde')
    batch.mkdir()
    (batch / 'new').mkdir()
    entries = []
    cache = Path(cache_dir) if cache_dir is not None else backups.parent / 'cache' / 'picons'
    # Pre-existing staged downloads from earlier NG builds are also reusable.
    old_downloads = {}
    needed = {p.get('sha256') for p in plan}
    for item in previous:
        folder = Path(item['path'])
        for entry in _journal(folder)['entries']:
            if entry['sha256'] in needed:
                old_downloads.setdefault(entry['sha256'], []).append(folder / 'new' / entry['name'])
    try:
        for item in plan:
            name = item['name']
            if not valid_filename(name) or not SHA.fullmatch(item.get('sha256', '')):
                raise ValueError('Plan invalide')
            check_url(item['url'])
            old_sha = digest(root / name)
            if 'old_sha256' in item and old_sha != item['old_sha256']:
                raise ValueError('Picon modifié depuis l’analyse : ' + name)
            cached = cache / (item['sha256'] + '.png')
            data = _verified_cached(cached, item['sha256'], expected_dimensions)
            if data is None:
                for prior in old_downloads.get(item['sha256'], []):
                    data = _verified_cached(prior, item['sha256'], expected_dimensions)
                    if data is not None:
                        break
            if data is None:
                data = fetch(item['url'])
            verify_png(data, expected_dimensions)
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('SHA256 incorrect : ' + name)
            if _verified_cached(cached, item['sha256'], expected_dimensions) is None:
                atomic_bytes(cached, data)
            atomic_bytes(batch / 'new' / name, data)
            entries.append(dict(item, old_sha256=old_sha))
        atomic_json(batch / 'transaction.json', {'schema': 2, 'state': 'staged', 'root': str(root),
                    'dimensions': list(expected_dimensions), 'entries': entries, 'date': batch.name})
        sync_dir(backups)
        return str(batch)
    except BaseException:
        shutil.rmtree(batch)
        raise


def _restore(batch, doc):
    root = Path(doc['root'])
    # Validate ALL preimages and current targets before changing a single file.
    for entry in doc['entries']:
        name, old = entry['name'], entry['old_sha256']
        if old is not None and digest(batch / 'old' / name) != old:
            raise ValueError('Sauvegarde corrompue : ' + name)
        if digest(root / name) not in (old, entry['sha256']):
            raise ValueError('Picon modifié après la mise à jour : ' + name)
    doc['state'] = 'restoring'
    atomic_json(batch / 'transaction.json', doc)
    for entry in reversed(doc['entries']):
        target = root / entry['name']
        if entry['old_sha256'] is not None:
            atomic_bytes(target, (batch / 'old' / entry['name']).read_bytes())
        elif target.exists():
            target.unlink()
            sync_dir(root)
    doc['state'] = 'restored'
    atomic_json(batch / 'transaction.json', doc)


def apply_staged(batch_path, picon_dir):
    batch = Path(batch_path)
    root = Path(picon_dir).resolve()
    with directory_lock(root):
        doc = _journal(batch)
        if doc['state'] != 'staged' or Path(doc['root']).resolve() != root:
            raise ValueError('Transaction déjà appliquée ou chemin différent')
        for entry in doc['entries']:
            if digest(root / entry['name']) != entry['old_sha256']:
                raise ValueError('Picon modifié depuis l’aperçu : ' + entry['name'])
            data = (batch / 'new' / entry['name']).read_bytes()
            verify_png(data, doc['dimensions'])
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Aperçu modifié ou corrompu')
        extra = sum(max(0, (batch / 'new' / e['name']).stat().st_size -
                        ((root / e['name']).stat().st_size if e['old_sha256'] else 0)) for e in doc['entries'])
        if shutil.disk_usage(root).free < extra + MAX_PNG + 1024 * 1024:
            raise OSError('Espace insuffisant dans le dossier de picons')
        (batch / 'old').mkdir(exist_ok=True)
        for entry in doc['entries']:
            if entry['old_sha256'] is not None:
                data = (root / entry['name']).read_bytes()
                if hashlib.sha256(data).hexdigest() != entry['old_sha256']:
                    raise ValueError('Picon modifié pendant la sauvegarde')
                atomic_bytes(batch / 'old' / entry['name'], data)
        # Durable write-ahead journal includes every target before ANY replacement.
        doc['state'] = 'applying'
        atomic_json(batch / 'transaction.json', doc)
        try:
            for entry in doc['entries']:
                target = root / entry['name']
                if digest(target) != entry['old_sha256']:
                    raise ValueError('Picon modifié pendant l’application')
                atomic_bytes(target, (batch / 'new' / entry['name']).read_bytes())
            doc['state'] = 'committed'
            atomic_json(batch / 'transaction.json', doc)
        except Exception:
            _restore(batch, doc)
            raise
    return {'updated': len(doc['entries']), 'backup': str(batch)}


def apply_plan(plan, picon_dir, backup_root, fetch=fetch_blob, expected_dimensions=(400, 240)):
    batch = stage_plan(plan, picon_dir, backup_root, fetch, expected_dimensions)
    return apply_staged(batch, picon_dir)


def restore_backup(batch_path, picon_dir):
    batch = Path(batch_path)
    root = Path(picon_dir).resolve()
    with directory_lock(root):
        doc = _journal(batch)
        if Path(doc['root']).resolve() != root or doc['state'] not in ('committed', 'applying', 'restoring'):
            raise ValueError('Restauration non applicable')
        _restore(batch, doc)
    return len(doc['entries'])


def list_backups(backup_root):
    result = []
    for path in sorted(Path(backup_root).glob('*/transaction.json'), reverse=True):
        doc = _journal(path.parent)
        result.append({'path': str(path.parent), 'date': doc['date'], 'state': doc['state'],
                       'count': len(doc['entries']), 'root': doc['root']})
    return result


def recover_pending(backup_root, picon_dir):
    recovered = []
    for item in list_backups(backup_root):
        if item['state'] in ('applying', 'restoring') and Path(item['root']).resolve() == Path(picon_dir).resolve():
            restore_backup(item['path'], picon_dir)
            recovered.append(item['date'])
    return recovered

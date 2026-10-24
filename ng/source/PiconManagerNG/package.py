# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified plugin package download. Installation requires a separate UI action."""
import hashlib
import io
import re
import tarfile
from pathlib import Path, PurePosixPath
from .network import read_json, read_source
from .storage import atomic_bytes

PACKAGE = 'enigma2-plugin-extensions-piconmanagerng'
RELEASE_URL = 'https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/ng/release.json'
MAX_IPK = 2 * 1024 * 1024
PREFIX = 'usr/lib/enigma2/python/Plugins/Extensions/PiconManagerNG/'


def version_key(version):
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)-r(\d+)', version)
    if not match:
        raise ValueError('Version invalide')
    return tuple(map(int, match.groups()))


def ar_members(blob):
    if not blob.startswith(b'!<arch>\n'):
        raise ValueError('Format IPK invalide')
    offset, members = 8, {}
    while offset < len(blob):
        header = blob[offset:offset+60]
        if len(header) != 60 or header[58:60] != b'`\n':
            raise ValueError('En-tête IPK invalide')
        name = header[:16].decode('ascii').strip().rstrip('/')
        size = int(header[48:58])
        end = offset + 60 + size
        if size < 0 or end > len(blob) or name in members:
            raise ValueError('Contenu IPK invalide')
        members[name] = blob[offset+60:end]
        offset = end + (size % 2)
    return members


def validate_package(blob, version):
    if len(blob) > MAX_IPK:
        raise ValueError('IPK trop volumineux')
    members = ar_members(blob)
    if members.get('debian-binary') != b'2.0\n' or set(members) != {'debian-binary', 'control.tar.gz', 'data.tar.gz'}:
        raise ValueError('Structure IPK invalide')
    with tarfile.open(fileobj=io.BytesIO(members['control.tar.gz'])) as archive:
        files = archive.getmembers()
        if len(files) != 1 or files[0].name not in ('control', './control') or not files[0].isfile():
            raise ValueError('Scripts d’installation non autorisés')
        control = archive.extractfile(files[0]).read(16384).decode('utf8')
    fields = dict(line.split(': ', 1) for line in control.splitlines() if ': ' in line)
    if fields.get('Package') != PACKAGE or fields.get('Version') != version or fields.get('Architecture') != 'all':
        raise ValueError('Métadonnées du paquet différentes de la version annoncée')
    with tarfile.open(fileobj=io.BytesIO(members['data.tar.gz'])) as archive:
        total = 0
        for item in archive:
            name = item.name.removeprefix('./')
            total += item.size
            if (not name.startswith(PREFIX) or '..' in PurePosixPath(name).parts or
                    not item.isfile() or item.size > MAX_IPK or total > 8 * MAX_IPK):
                raise ValueError('Le paquet contient un chemin non autorisé')
    return fields


def check_release():
    doc = read_json(RELEASE_URL, 65536)
    if (doc.get('schema') != 1 or doc.get('status') != 'stable' or
            doc.get('package') != PACKAGE or not re.fullmatch(r'\d+\.\d+\.\d+-r\d+', doc.get('version', '')) or
            not re.fullmatch('[a-f0-9]{64}', doc.get('sha256', '')) or
            not isinstance(doc.get('size'), int) or not 0 < doc['size'] <= MAX_IPK):
        raise ValueError('Aucune version NG stable vérifiée disponible')
    from .updates import check_url
    check_url(doc.get('url', ''))
    return doc


def download_release(doc, cache_dir):
    from .updates import check_url
    check_url(doc['url'])
    blob = read_source(doc['url'], MAX_IPK)
    if len(blob) != doc['size'] or hashlib.sha256(blob).hexdigest() != doc['sha256']:
        raise ValueError('Intégrité du paquet incorrecte')
    validate_package(blob, doc['version'])
    path = Path(cache_dir) / (PACKAGE + '_' + doc['version'] + '_all.ipk')
    atomic_bytes(path, blob)
    return path


def install_release(path, doc, data_dir):
    """Called only after the user confirms this specific verified version."""
    import subprocess
    import datetime
    blob = Path(path).read_bytes()
    if hashlib.sha256(blob).hexdigest() != doc['sha256'] or len(blob) != doc['size']:
        raise ValueError('Le paquet a changé depuis sa vérification')
    validate_package(blob, doc['version'])
    current = Path('/' + PREFIX.rstrip('/'))
    if current.is_dir():
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz') as archive:
            for file in current.iterdir():
                if file.is_symlink():
                    raise ValueError('Installation contenant un lien symbolique')
                if file.is_file():
                    archive.add(file, arcname=file.name, recursive=False)
        name = 'plugin-' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S') + '.tar.gz'
        atomic_bytes(Path(data_dir) / 'plugin-backups' / name, output.getvalue())
    result = subprocess.run(['opkg', 'install', str(path)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError('Installation non terminée. Sauvegarde du plugin conservée.')
    return doc['version']

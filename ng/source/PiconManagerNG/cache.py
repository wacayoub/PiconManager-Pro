# SPDX-License-Identifier: GPL-3.0-or-later
"""Persistent local inventory. Opening the dashboard reads only a tiny summary."""
import gzip
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from .core import valid_filename
from .groups import summarize
from .storage import atomic_json, directory_lock, sync_dir


class InventoryCache:
    def __init__(self, directory, context):
        self.directory = Path(directory)
        self.context = context
        self.key = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:20]
        self.summary_path = self.directory / ('inventory-' + self.key + '.json')

    def summary(self):
        try:
            doc = json.loads(self.summary_path.read_text(encoding='utf8'))
            if (doc.get('schema') != 1 or doc.get('context') != self.context or
                    not re.fullmatch('services-' + self.key + r'-[0-9a-f]{32}\.gz', doc.get('file', '')) or
                    not isinstance(doc.get('counts'), dict) or
                    not all(isinstance(v, int) and v >= 0 for v in doc['counts'].values()) or
                    not isinstance(doc.get('created_at'), (int, float)) or
                    not (self.directory / doc['file']).is_file()):
                return None
            return doc
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def save(self, services, counts):
        with directory_lock(self.directory):
            name = 'services-' + self.key + '-' + uuid.uuid4().hex + '.gz'
            destination = self.directory / name
            fd, temp = tempfile.mkstemp(prefix='.inventory-', dir=str(self.directory))
            try:
                with os.fdopen(fd, 'wb') as raw:
                    with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as stream:
                        for service in services:
                            # The cache never retains an IPTV URL, even for imported records.
                            row = {key: service[key] for key in ('ref', 'identity', 'name', 'picon', 'srp_key',
                                   'kind', 'radio', 'bouquet', 'installed') if key in service}
                            row['ref'] = ':'.join(row.get('ref', '').split(':')[:10]) + ':'
                            stream.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf8'))
                    raw.flush()
                    os.fsync(raw.fileno())
                os.replace(temp, destination)
                sync_dir(self.directory)
                doc = {'schema': 1, 'context': self.context, 'file': name, 'counts': dict(counts),
                       'created_at': time.time(), 'rows': len(services), 'groups': summarize(services)}
                atomic_json(self.summary_path, doc)
                # Only replace this context's own snapshots. Other paths/radio settings stay reusable.
                for old in self.directory.glob('services-' + self.key + '-*.gz'):
                    if old.name != name:
                        try:
                            old.unlink()
                        except OSError:
                            pass  # a reader may still have this file open on Windows
                return doc
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)

    def load(self):
        for attempt in range(2):
            doc = self.summary()
            if doc is None:
                raise ValueError('Vos chaînes ne sont pas encore mémorisées. Réglages → Actualiser mes chaînes.')
            try:
                services = []
                with gzip.open(self.directory / doc['file'], 'rt', encoding='utf8') as stream:
                    for line in stream:
                        row = json.loads(line)
                        if not isinstance(row, dict) or '://' in row.get('ref', '') or row.get('ref', '').count(':') != 10:
                            raise ValueError('Inventaire mémorisé invalide')
                        if row.get('picon') and not valid_filename(row['picon']):
                            raise ValueError('Nom de picon mémorisé invalide')
                        services.append(row)
                if len(services) != doc['rows']:
                    raise ValueError('Inventaire mémorisé incomplet')
                return services, doc
            except FileNotFoundError:
                if attempt == 0:
                    continue  # a manual refresh published a newer snapshot between open/read
            except (OSError, EOFError, ValueError, TypeError, KeyError, UnicodeError) as exc:
                raise ValueError('Les données mémorisées sont illisibles. Réglages → Actualiser mes chaînes.') from exc
        raise ValueError('Actualisez mes chaînes depuis les réglages.')

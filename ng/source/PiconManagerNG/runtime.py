# SPDX-License-Identifier: GPL-3.0-or-later
"""Application operations. Called by GUI workers, independently testable."""
import json
import os
import platform
from collections import Counter
from pathlib import Path
from . import core, catalog, profile, updates, lyngsat
from .network import read_json
from .storage import atomic_json

VERSION = '2.0.0'
DATA = Path('/var/lib/piconmanager-ng')
DEFAULT_MANIFEST = 'https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/dev/piconmanager-ng-v2/ng/catalog/manifest.json'


def detect_paths(settings='/etc/enigma2/settings'):
    candidates = []
    try:
        for line in Path(settings).read_text(encoding='utf8').splitlines():
            key, _, value = line.partition('=')
            if ((key.startswith('config.picon.') and key.endswith('.path')) or
                    (key.startswith('config.plugins.chocholousekpicons.') and key.endswith('.picon_folder'))):
                candidates.append(value.rstrip('/'))
    except OSError:
        pass
    candidates += ['/usr/share/enigma2/picon', '/picon', '/media/hdd/picon', '/media/usb/picon']
    return list(dict.fromkeys(p for p in candidates if Path(p).is_dir()))


class Manager:
    def __init__(self, data_dir=DATA, bouquets='/etc/enigma2', paths=None):
        self.data = Path(data_dir)
        self.bouquets = Path(bouquets)
        self.paths = paths if paths is not None else detect_paths()
        self.settings = {'picon_dir': (self.paths or ['/usr/share/enigma2/picon'])[0],
                         'include_radio': True, 'overwrite': False, 'manifest_url': DEFAULT_MANIFEST}
        try:
            self.settings.update(json.loads((self.data / 'settings.json').read_text(encoding='utf8')))
        except (OSError, ValueError):
            pass
        if self.settings['picon_dir'] not in self.paths:
            self.settings['picon_dir'] = (self.paths or ['/usr/share/enigma2/picon'])[0]
        self.services, self.counts, self.plan = [], {}, []
        self.catalog = None
        self.aliases = self._read('aliases.json', {})
        self.profile = self._read('profile.json', None)
        self._profile_target = self.settings['picon_dir']
        self.lyngsat = None
        self.staged = None

    def _read(self, name, default):
        try:
            return json.loads((self.data / name).read_text(encoding='utf8'))
        except (OSError, ValueError):
            return default

    @property
    def target(self):
        return Path(self.settings['picon_dir'])

    @property
    def backups(self):
        return self.data / 'backups'

    def save_settings(self):
        if self.settings['picon_dir'] not in self.paths:
            raise ValueError('Dossier de picons inconnu')
        atomic_json(self.data / 'settings.json', self.settings)
        self.plan, self.staged = [], None
        if self.settings['picon_dir'] != self._profile_target:
            self.profile = None
            self._profile_target = self.settings['picon_dir']
            (self.data / 'profile.json').unlink(missing_ok=True)

    def scan(self, progress=None):
        self.services = core.scan_bouquet_files(self.bouquets, self.settings['include_radio'], progress)
        # Inventory describes the chosen destination; alternative packs cannot hide missing files.
        self.counts = core.find_installed(self.services, self.target)
        self.counts.update(Counter(s['kind'] for s in self.services))
        self.catalog = None
        self.plan, self.staged = [], None
        return self.counts

    def capture_profile(self):
        paths = list(dict.fromkeys(s['installed'] for s in self.services if s.get('installed')))[:8]
        self.profile = profile.capture_profile(paths)
        atomic_json(self.data / 'profile.json', self.profile)
        return self.profile

    def sync_catalog(self, force=False):
        if not self.services:
            self.scan()
        self.catalog = catalog.load_catalog(self.services, self.data / 'cache', force)
        for service in self.services:
            service['match'] = catalog.match_service(service, self.catalog, self.aliases)
        return {'matched': sum(bool(s['match']['logo']) for s in self.services),
                'ambiguous': sum(s['match']['method'] == 'Ambigu' for s in self.services),
                'commit': self.catalog['commit']}

    def set_alias(self, service, logo):
        if logo not in service.get('match', {}).get('candidates', []):
            raise ValueError('Choix absent du catalogue')
        self.aliases[catalog.alias_key(service)] = logo
        atomic_json(self.data / 'aliases.json', self.aliases)
        service['match'] = catalog.match_service(service, self.catalog, self.aliases)

    def check_updates(self):
        if not self.catalog:
            self.sync_catalog()
        if not self.profile:
            self.capture_profile()
        try:
            doc = read_json(self.settings['manifest_url'])
        except Exception as exc:
            raise RuntimeError('Catalogue de PNG du profil indisponible. Les originaux sont conservés.') from exc
        profile.validate_style(doc, self.profile)
        manifest = catalog.materialize_manifest(doc, self.services)
        self.plan = updates.plan_replacements(self.services, self.target, manifest,
                                              self.profile['style_id'], self.settings['overwrite'])
        return self.plan

    def stage(self, selected):
        if not self.profile:
            raise ValueError('Profil visuel absent')
        self.staged = updates.stage_plan(selected, self.target, self.backups,
                                         expected_dimensions=self.profile['dimensions'])
        return self.staged

    def apply(self):
        if not self.staged:
            raise ValueError('Aucun aperçu préparé')
        result = updates.apply_staged(self.staged, self.target)
        self.staged = None
        self.scan()
        return result

    def lookup_lyngsat(self):
        if not self.services:
            self.scan()
        missing = [s for s in self.services if not s.get('installed')]
        self.lyngsat = lyngsat.lookup_services(missing, self.data / 'cache')
        return self.lyngsat

    def diagnostics(self):
        import shutil
        return {'version': VERSION, 'python': platform.python_version(), 'picon_dir': str(self.target),
                'free_mb': shutil.disk_usage(self.target).free // (1024 * 1024),
                'counts': self.counts, 'catalog_commit': (self.catalog or {}).get('commit', '—'),
                'style': (self.profile or {}).get('style_id', 'Non mesuré'),
                'backups': len(updates.list_backups(self.backups))}

# SPDX-License-Identifier: GPL-3.0-or-later
"""PiconManager NG Neo Dark, independent of the active Metrix skin."""
from pathlib import Path
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from enigma import getDesktop
from .runtime import Manager, VERSION
from .gui import Worker, Browser
from . import updates

ENTRIES = ('Mes chaînes et picons', 'Picons manquants', 'Mises à jour GitHub',
           'Sources et correspondances', 'LyngSat Logo', 'Style Chocholousek',
           'Sauvegardes et restauration', 'Réglages', 'Diagnostic et version')

def neo_dark_skin(desktop_width):
    """Use the active Enigma2 desktop geometry (HD and FHD skins)."""
    large = desktop_width >= 1800
    width, height = (1920, 1080) if large else (1280, 720)
    def scaled(n):
        return int(round(n * (1.5 if large else 1)))
    def rect(x, y, w, h):
        return '%d,%d' % (scaled(x), scaled(y)), '%d,%d' % (scaled(w), scaled(h))
    def widget(name, x, y, w, h, font=29, bg='#111B2C', fg='#F1F5FE', extra=''):
        pos, size = rect(x, y, w, h)
        return ('<widget name="%s" position="%s" size="%s" font="Regular;%d" '
                'foregroundColor="%s" backgroundColor="%s" %s />' %
                (name, pos, size, scaled(font), fg, bg, extra))
    def pane(x, y, w, h, color):
        pos, size = rect(x, y, w, h)
        return '<eLabel position="%s" size="%s" backgroundColor="%s" />' % (pos, size, color)
    return ('''<screen name="PiconManagerNGScreen" position="center,center" size="%d,%d"
        title="PiconManager NG" backgroundColor="#080D18" flags="wfNoBorder">''' % (width, height) +
        pane(0, 0, 1280, 720, '#080D18') +
        pane(44, 128, 726, 477, '#111B2C') +
        pane(44, 128, 6, 477, '#24C7F5') +
        pane(800, 128, 435, 477, '#111B2C') +
        pane(800, 128, 435, 6, '#8367EB') +
        widget('title', 46, 33, 730, 57, 43, '#080D18') +
        widget('subtitle', 49, 93, 680, 33, 20, '#080D18', '#9CAECB') +
        widget('menu', 80, 165, 648, 398, 24, '#111B2C', '#F1F5FE',
               'itemHeight="%d" foregroundColorSelected="#FFFFFF" backgroundColorSelected="#244461" enableWrapAround="1"' % scaled(42)) +
        widget('info_title', 830, 165, 365, 47, 28, '#111B2C') +
        widget('count_title', 830, 232, 365, 33, 22, '#111B2C', '#9CAECB') +
        widget('count_value', 830, 273, 365, 72, 48, '#111B2C', '#FFFFFF') +
        widget('available_title', 830, 367, 365, 33, 22, '#111B2C', '#9CAECB') +
        widget('available_value', 830, 407, 365, 67, 43, '#111B2C', '#24C7F5') +
        widget('status', 830, 515, 365, 64, 21, '#111B2C', '#9CAECB') +
        widget('footer', 49, 637, 1180, 40, 22, '#080D18', '#BAC7DF') +
        '</screen>')


class PiconManagerNGScreen(Screen, Worker):
    def __init__(self, session):
        self.skin = neo_dark_skin(getDesktop(0).size().width())
        Screen.__init__(self, session)
        self.manager = Manager()
        self['title'] = Label('PiconManager NG')
        self['subtitle'] = Label('NEO DARK  •  SAT + IPTV  •  ' + VERSION)
        self['menu'] = MenuList(list(ENTRIES))
        self['info_title'] = Label('Mes chaînes')
        self['count_title'] = Label('Chaînes détectées')
        self['count_value'] = Label('—')
        self['available_title'] = Label('Picons disponibles')
        self['available_value'] = Label('—')
        self['status'] = Label('Prêt à analyser')
        self['footer'] = Label('OK Ouvrir   VERT Analyser   JAUNE Manquants   BLEU Réglages   ROUGE Quitter')
        self['keys'] = ActionMap(['OkCancelActions', 'ColorActions', 'MenuActions', 'DirectionActions'],
            {'ok': self.select, 'cancel': self.leave, 'red': self.leave, 'green': self.scan,
             'yellow': lambda: self.channels(True), 'blue': self.settings, 'menu': self.settings,
             'up': self['menu'].up, 'down': self['menu'].down,
             'left': self['menu'].pageUp, 'right': self['menu'].pageDown}, -1)
        self.setup_worker()
        self.onLayoutFinish.append(self.scan)

    def info(self, text):
        self.session.open(MessageBox, text, MessageBox.TYPE_INFO)

    def refresh_counts(self, _=None):
        c = self.manager.counts
        self['count_value'].setText(str(c.get('total', 0)))
        self['available_value'].setText(str(c.get('found', 0)))
        self['status'].setText('%d manquants • %d sans identité' % (c.get('missing', 0), c.get('unsupported', 0)))

    def scan(self):
        self.work(lambda: self.manager.scan(self.progress), self.refresh_counts)

    def select(self):
        if self.busy:
            return
        index = self['menu'].getSelectedIndex()
        actions = [lambda: self.channels(False), lambda: self.channels(True), self.check_updates,
                   self.sources, self.lyngsat, self.style, self.backups, self.settings, self.diagnostics]
        if 0 <= index < len(actions):
            actions[index]()

    def channels(self, missing=False):
        if self.busy:
            return
        mode = {'value': 2 if missing else 0}
        def filtered():
            return [('%s  ·  %s' % (s['name'] or 'Sans nom', s['kind']), s) for s in self.manager.services
                    if mode['value'] == 0 or bool(s.get('installed')) == (mode['value'] == 1)]
        rows = filtered()
        def detail(row):
            s = row[1]
            match = s.get('match', {})
            return ('%s\n%s • %s' % (s['name'] or 'Sans nom', s['kind'], match.get('method', 'Catalogue non consulté')),
                    s.get('installed'), None)
        def choose(view):
            row = view.row()
            if not row:
                return
            s = row[1]
            choices = s.get('match', {}).get('candidates', [])
            if not choices:
                self.info('Consultez les sources pour rechercher les correspondances GitHub.')
                return
            def selected(value):
                if value:
                    self.manager.set_alias(s, value[1])
                    view.focus()
            self.session.openWithCallback(selected, ChoiceBox, title='Choisir le logo de cette chaîne',
                                          list=[(x, x) for x in choices])
        def filter_rows(view):
            mode['value'] = (mode['value'] + 1) % 3
            view.items, view.page = filtered(), 0
            view['title'].setText(('Mes chaînes', 'Picons présents', 'Picons manquants')[mode['value']])
            view.refresh()
        self.session.open(Browser, 'Picons manquants' if missing else 'Mes chaînes et picons', rows,
                          detail=detail, yellow=choose, blue=filter_rows,
                          footer='←→ Pages   BLEU Filtrer   JAUNE Correspondance   ROUGE Retour')

    def sources(self):
        def done(result):
            self.info('GitHub picons/picons\n%d correspondances • %d ambiguïtés\nRévision : %s\n\nLes ambiguïtés se choisissent dans Mes chaînes.' %
                      (result['matched'], result['ambiguous'], result['commit'][:12]))
        self.work(self.manager.sync_catalog, done)

    def lyngsat(self):
        def done(result):
            from .catalog import name_key
            rows = []
            for service in self.manager.services:
                matches = result['matches'].get(name_key(service.get('name', '')), [])
                if matches:
                    rows.append((service['name'] + ' · %d logo(s)' % len(matches), (service, matches)))
            def detail(row):
                service, matches = row[1]
                return (service['name'] + '\nLyngSat : %d source(s)' % len(matches), service.get('installed'), None)
            def preview(view):
                row = view.row()
                if not row:
                    return
                service, matches = row[1]
                def download():
                    import hashlib
                    from .network import read_source
                    from .storage import atomic_bytes
                    blob = read_source(matches[0]['url'], updates.MAX_PNG)
                    # View source PNGs; never restyle/rasterize SVG on the receiver.
                    from PIL import Image
                    import io
                    with Image.open(io.BytesIO(blob)) as image:
                        if image.format not in ('PNG', 'WEBP') or max(image.size) > 4096:
                            raise ValueError('Source à préparer hors récepteur avant aperçu')
                        image.load()
                        from PIL import ImageOps
                        fitted = ImageOps.contain(image.convert('RGBA'), (400, 240))
                        canvas = Image.new('RGBA', (400, 240), (0, 0, 0, 0))
                        canvas.alpha_composite(fitted, ((400-fitted.width)//2, (240-fitted.height)//2))
                        dest = self.manager.data / 'cache' / ('lyngsat-preview-' + hashlib.sha256(blob).hexdigest()[:16] + '.png')
                        output = io.BytesIO()
                        canvas.save(output, format='PNG')
                    atomic_bytes(dest, output.getvalue())
                    return dest
                def ready(path):
                    view.detail_callback = lambda r: detail(r) if r != row else (service['name'] + '\nSource LyngSat • style non appliqué', service.get('installed'), path)
                    view.focus()
                view.work(download, ready)
            self.session.open(Browser, 'LyngSat Logo · %d indexés · %d pages indisponibles' %
                              (result['indexed'], len(result['failed_letters'])), rows, detail=detail, green=preview,
                              footer='VERT Aperçu source   ←→ Pages   ROUGE Retour')
        self.work(self.manager.lookup_lyngsat, done)

    def style(self):
        def done(value):
            self.info('Originaux Chocholousek\n%d × %d • %d échantillons conservés\nFond transparent : %s\n\nProfil : %s\nLes logos proposés doivent correspondre à ce profil.' %
                (*value['dimensions'], len(value['samples']),
                 'oui' if all(s['transparent'] for s in value['samples']) else 'non uniforme', value['style_id']))
        self.work(self.manager.capture_profile, done)

    def check_updates(self):
        def done(plan):
            if not plan:
                self.info('Aucune mise à jour vérifiée pour les chaînes et le profil actuels.')
                return
            names = {s['picon']: s['name'] for s in self.manager.services}
            for p in plan:
                p['label'] = names.get(p['name']) or p['name']
            rows = [(('%s · %s' % ('Remplacer' if p['action'] == 'replace' else 'Ajouter', p['label'])), p) for p in plan]
            def prepare(view):
                selected = [view.items[i][1] for i in sorted(view.selected)]
                if not selected:
                    self.info('Sélectionnez les picons à préparer avec OK ou JAUNE.')
                    return
                def ready(batch):
                    self.preview(batch, selected)
                view.work(lambda: self.manager.stage(selected), ready)
            self.session.open(Browser, 'Mises à jour disponibles', rows, selectable=True, green=prepare,
                detail=lambda row: (row[1]['action'] + '\n' + row[1]['name'], str(self.manager.target / row[1]['name']), None),
                footer='OK Sélectionner   JAUNE Tout/aucun   VERT Préparer   ←→ Pages   ROUGE Retour')
        self.work(self.manager.check_updates, done)

    def preview(self, batch, entries):
        rows = [(p.get('label', p['name']), p) for p in entries]
        def detail(row):
            name = row[1]['name']
            return (name + '\nPrêt • empreinte vérifiée', self.manager.target / name, Path(batch) / 'new' / name)
        def apply(view):
            def confirmed(value):
                if value:
                    def done(result):
                        view['status'].setText('%d picons appliqués • sauvegarde disponible' % result['updated'])
                        view.callbacks['green'] = None
                        view['footer'].setText('↑↓ Comparer   ←→ Pages   ROUGE Retour')
                        self.refresh_counts()
                    view.work(self.manager.apply, done)
            self.session.openWithCallback(confirmed, MessageBox,
                'Appliquer les %d picons sélectionnés ?\nLes originaux seront sauvegardés avant remplacement.' % len(entries),
                MessageBox.TYPE_YESNO, default=False)
        self.session.open(Browser, 'Aperçu avant / après', rows, detail=detail, green=apply,
                          footer='↑↓ Comparer   ←→ Pages   VERT Appliquer   ROUGE Annuler')

    def backups(self):
        def done(items):
            rows = [('%s · %d · %s' % (x['date'], x['count'], x['state']), x) for x in items]
            def restore(view):
                row = view.row()
                if not row or row[1]['state'] not in ('committed', 'applying', 'restoring'):
                    return
                item = row[1]
                def confirm(value):
                    if value:
                        def task():
                            updates.restore_backup(item['path'], self.manager.target)
                            return self.manager.scan()
                        def ready(value):
                            item['state'] = 'restored'
                            self.refresh_counts()
                            view['status'].setText('Restauration terminée')
                        view.work(task, ready)
                self.session.openWithCallback(confirm, MessageBox,
                    'Restaurer les %d picons de cette sauvegarde ?' % item['count'], MessageBox.TYPE_YESNO, default=False)
            self.session.open(Browser, 'Sauvegardes et récupération', rows, green=restore,
                              footer='VERT Restaurer   ←→ Pages   ROUGE Retour')
        self.work(lambda: updates.list_backups(self.manager.backups), done)

    def settings(self):
        if self.busy:
            return
        s = self.manager.settings
        options = [('Destination : ' + s['picon_dir'], 'path'),
                   ('Radios : ' + ('oui' if s['include_radio'] else 'non'), 'radio'),
                   ('Remplacer les existants : ' + ('oui' if s['overwrite'] else 'non'), 'overwrite')]
        def changed(value):
            if not value:
                return
            key = value[1]
            if key == 'path':
                def set_path(choice):
                    if choice:
                        s['picon_dir'] = choice[1]
                        self.manager.save_settings()
                        self.scan()
                self.session.openWithCallback(set_path, ChoiceBox, title='Dossier de picons',
                                              list=[(p, p) for p in self.manager.paths])
            else:
                setting = 'include_radio' if key == 'radio' else 'overwrite'
                s[setting] = not s[setting]
                self.manager.save_settings()
                self.scan()
        self.session.openWithCallback(changed, ChoiceBox, title='Réglages', list=options)

    def diagnostics(self):
        if self.busy:
            return
        def choose(value):
            if value and value[1] == 'update':
                self.plugin_update()
            elif value:
                self.show_diagnostics()
        self.session.openWithCallback(choose, ChoiceBox, title='Diagnostic et version',
                                      list=[('Diagnostic local', 'local'), ('Version du plugin sur GitHub', 'update')])

    def plugin_update(self):
        from . import package
        def ready(doc):
            installed = package.version_key(VERSION + '-r0')
            offered = package.version_key(doc['version'])
            if offered <= installed:
                self.info('Le plugin est à jour : ' + VERSION)
                return
            def downloaded(path):
                def confirm(value):
                    if value:
                        self.work(lambda: package.install_release(path, doc, self.manager.data),
                                  lambda version: self.info('Version %s installée. Aucun redémarrage automatique.' % version))
                self.session.openWithCallback(confirm, MessageBox,
                    'Paquet %s vérifié.\nInstaller cette version ?\nLe plugin actuel sera sauvegardé.' % doc['version'],
                    MessageBox.TYPE_YESNO, default=False)
            self.work(lambda: package.download_release(doc, self.manager.data / 'cache'), downloaded)
        self.work(package.check_release, ready)

    def show_diagnostics(self):
        def done(d):
            self.info('PiconManager NG %s\nPython %s\nDestination : %s\nLibre : %d Mo\nSauvegardes : %d\nSAT : %d • IPTV : %d\nProfil : %s' %
                (d['version'], d['python'], d['picon_dir'], d['free_mb'], d['backups'],
                 d['counts'].get('SAT', 0), d['counts'].get('IPTV', 0), d['style']))
        self.work(self.manager.diagnostics, done)


def open_plugin(session, **kwargs):
    session.open(PiconManagerNGScreen)


def Plugins(**kwargs):
    return PluginDescriptor(name='PiconManager NG', description='Mes picons · Neo Dark · SAT et IPTV',
                            where=PluginDescriptor.WHERE_PLUGINMENU, fnc=open_plugin)

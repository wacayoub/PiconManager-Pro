# SPDX-License-Identifier: GPL-3.0-or-later
"""Neo Dark Enigma2 GUI; read-only until style and receiver checks complete."""
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from enigma import getDesktop
from .core import scan_bouquet_files, find_installed

BOUQUETS = '/etc/enigma2'
PICONS = '/usr/share/enigma2/picon'

ENTRIES = (
    'Analyser mes chaînes',
    'Voir mes picons',
    'Style Chocholousek',
    'Mises à jour GitHub',
    'À propos du plugin',
)

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
        widget('menu', 80, 165, 648, 398, 29, '#111B2C', '#F1F5FE',
               'itemHeight="%d"' % scaled(72)) +
        widget('info_title', 830, 165, 365, 47, 28, '#111B2C') +
        widget('count_title', 830, 232, 365, 33, 22, '#111B2C', '#9CAECB') +
        widget('count_value', 830, 273, 365, 72, 48, '#111B2C', '#FFFFFF') +
        widget('available_title', 830, 367, 365, 33, 22, '#111B2C', '#9CAECB') +
        widget('available_value', 830, 407, 365, 67, 43, '#111B2C', '#24C7F5') +
        widget('status', 830, 515, 365, 64, 21, '#111B2C', '#9CAECB') +
        widget('footer', 49, 637, 1180, 40, 22, '#080D18', '#BAC7DF') +
        '</screen>')

class PiconManagerNGScreen(Screen):
    def __init__(self, session):
        try:
            desktop_width = getDesktop(0).size().width()
        except Exception:
            desktop_width = 1280
        self.skin = neo_dark_skin(desktop_width)
        Screen.__init__(self, session)
        self['title'] = Label('PiconManager NG')
        self['subtitle'] = Label('NEO DARK  |  SAT + IPTV  |  OpenATV')
        self['menu'] = MenuList(list(ENTRIES))
        self['info_title'] = Label('Vue d’ensemble')
        self['count_title'] = Label('Chaînes détectées')
        self['count_value'] = Label('—')
        self['available_title'] = Label('Picons disponibles')
        self['available_value'] = Label('—')
        self['status'] = Label('Mode protégé : lecture seule')
        self['footer'] = Label('OK Sélectionner    VERT Analyser    JAUNE Informations    ROUGE Quitter')
        self['keys'] = ActionMap(['OkCancelActions', 'ColorActions'],
                                 {'ok': self.select, 'cancel': self.close,
                                  'red': self.close, 'green': self.scan,
                                  'yellow': self.about}, -1)

    def scan(self):
        try:
            services = scan_bouquet_files(BOUQUETS)
            counts = find_installed(services, PICONS)
            self['count_value'].setText(str(counts['total']))
            self['available_value'].setText(str(counts['found']))
            self['status'].setText('%d manquants  •  %d sans SRP' %
                                   (counts['missing'], counts['unsupported']))
        except Exception as exc:
            self['status'].setText('Analyse impossible')
            self.session.open(MessageBox, str(exc), MessageBox.TYPE_ERROR)

    def about(self):
        self.session.open(MessageBox,
                          'PiconManager NG 2.0.0-dev1 — Neo Dark.\n'
                          'Analyse locale disponible.\n'
                          'Synchronisation GitHub et remplacement désactivés jusqu’aux tests récepteur.',
                          MessageBox.TYPE_INFO)

    def select(self):
        selected = self['menu'].getCurrent()
        if selected is None:
            return
        if selected.startswith('Analyser') or selected.startswith('Voir'):
            self.scan()
        elif selected.startswith('À propos'):
            self.about()
        elif selected.startswith('Style'):
            self.session.open(MessageBox,
                              'Profil visuel actuel : à identifier sur le Vu+.\n'
                              'Les picons Chocholousek ne seront pas remplacés par un autre style.',
                              MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox,
                              'Catalogue GitHub en préparation.\nAucune mise à jour appliquée.',
                              MessageBox.TYPE_INFO)

def open_plugin(session, **kwargs):
    session.open(PiconManagerNGScreen)

def Plugins(**kwargs):
    return PluginDescriptor(name='PiconManager NG',
                            description='Picons modernes — Neo Dark',
                            where=PluginDescriptor.WHERE_PLUGINMENU,
                            fnc=open_plugin)

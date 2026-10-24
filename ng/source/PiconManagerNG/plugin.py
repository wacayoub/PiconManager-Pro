# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only Enigma2 GUI prototype (hardware validation pending)."""
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from .core import scan_bouquet_files, find_installed

BOUQUETS = '/etc/enigma2'
PICONS = '/usr/share/enigma2/picon'

class PiconManagerNGScreen(Screen):
    skin = '''<screen name="PiconManagerNG" position="center,center" size="1280,720" title="PiconManager NG">
      <widget name="title" position="60,45" size="1160,70" font="Regular;40" foregroundColor="#f6f6ff" backgroundColor="#141b2e" />
      <widget name="menu" position="60,135" size="1160,420" itemHeight="80" font="Regular;32" foregroundColor="#f6f6ff" backgroundColor="#141b2e" selectionColor="#536a9f" />
      <widget name="status" position="60,580" size="1160,70" font="Regular;24" foregroundColor="#bfc9df" backgroundColor="#141b2e" />
    </screen>'''
    def __init__(self,session):
        Screen.__init__(self,session)
        self['title'] = Label('PiconManager NG 2027')
        self['menu'] = MenuList(['Analyser les bouquets (lecture seule)',
                                 'Picons présents / manquants', 'À propos'])
        self['status'] = Label('Mode sécurisé : aucun remplacement automatique')
        self['keys'] = ActionMap(['OkCancelActions'],
                                 {'ok':self.select,'cancel':self.close},-1)
    def select(self):
        item = self['menu'].getCurrent()
        if item.startswith('À propos'):
            msg = 'PiconManager NG 2.0.0-dev1. Le style Chocholousek sera conservé après calibration.'
        else:
            services = scan_bouquet_files(BOUQUETS)
            counts = find_installed(services,PICONS)
            msg = ('Services : %(total)d\nPicons trouvés : %(found)d\n'
                   'Manquants : %(missing)d\nServices sans SRP valide : %(unsupported)d\n'
                   'Aucune modification effectuée.' % counts)
        self.session.open(MessageBox,msg,MessageBox.TYPE_INFO)

def open_plugin(session,**kwargs):
    session.open(PiconManagerNGScreen)

def Plugins(**kwargs):
    return PluginDescriptor(name='PiconManager NG',
                            description='Picons GitHub / Chocholousek',
                            where=PluginDescriptor.WHERE_PLUGINMENU,
                            fnc=open_plugin)

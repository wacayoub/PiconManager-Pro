"""Exercise native component contracts with a small Enigma2-free UI harness."""
import importlib
import sys
import types
import unittest
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class Component:
    def __init__(self, value=None, *args, **kwargs):
        self.value = value
        self.instance = MagicMock()
        self.onSelectionChanged = []
        self.index = 0
        self.actions = args[0] if args and isinstance(args[0], dict) else {}
    def setText(self, value): self.value = value
    def setList(self, value): self.value = value
    def getCurrent(self): return self.value[self.index] if self.value else None
    def getSelectedIndex(self): return self.index
    def show(self): pass
    def hide(self): pass
    def up(self):
        self.index = max(0, self.index-1)
        for callback in self.onSelectionChanged: callback()
    def down(self):
        self.index = min(len(self.value)-1, self.index+1)
        for callback in self.onSelectionChanged: callback()
    def pageUp(self): self.up()
    def pageDown(self): self.down()


class Screen(dict):
    def __init__(self, session):
        self.session = session
        self.onClose = []
        self.onLayoutFinish = []
    def close(self):
        # Enigma2 Screen.deleteGUIScreen and doClose iterate self.items().
        for callback in self.onClose: callback()
        for name, value in list(self.items()):
            del self[name]
        self.closed = True


def fake_modules():
    modules = {}
    objects = {'Screens.Screen': ('Screen', Screen), 'Screens.MessageBox': ('MessageBox', MagicMock()),
               'Screens.ChoiceBox': ('ChoiceBox', MagicMock()), 'Components.ActionMap': ('ActionMap', Component),
               'Components.Label': ('Label', Component), 'Components.MenuList': ('MenuList', Component),
               'Components.Pixmap': ('Pixmap', Component), 'Plugins.Plugin': ('PluginDescriptor', MagicMock())}
    for path, (name, obj) in objects.items():
        mod = types.ModuleType(path)
        setattr(mod, name, obj)
        modules[path] = mod
        root = path.split('.')[0]
        modules.setdefault(root, types.ModuleType(root))
    enigma = types.ModuleType('enigma')
    enigma.getDesktop = lambda x: MagicMock()
    enigma.eTimer = lambda: types.SimpleNamespace(callback=[], start=lambda *a: None, stop=lambda: None)
    modules['enigma'] = enigma
    return modules


class NeoDark(unittest.TestCase):
    def setUp(self):
        self.patch = patch.dict(sys.modules, fake_modules())
        self.patch.start()
        self.gui = importlib.import_module('PiconManagerNG.gui')
        self.plugin = importlib.import_module('PiconManagerNG.plugin')
        self.addCleanup(self.patch.stop)
        self.addCleanup(lambda: sys.modules.pop('PiconManagerNG.gui', None))
        self.addCleanup(lambda: sys.modules.pop('PiconManagerNG.plugin', None))

    def test_hd_fhd_geometry_and_named_components(self):
        for width, height in ((1280, 720), (1920, 1080)):
            for skin in (self.gui.browser_skin(width), self.plugin.neo_dark_skin(width)):
                root = ET.fromstring(skin)
                self.assertEqual(root.attrib['size'], '%d,%d' % (width, height))
                for node in root:
                    x, y = map(int, node.attrib['position'].split(','))
                    w, h = map(int, node.attrib['size'].split(','))
                    self.assertLessEqual(x + w, width)
                    self.assertLessEqual(y + h, height)
                menu = next(n for n in root if n.attrib.get('name') in ('rows', 'menu'))
                self.assertIn('backgroundColorSelected', menu.attrib)

    def test_large_channel_browser_keeps_visible_page_bounded_and_selection_stable(self):
        with patch.object(self.gui, 'getDesktop', lambda _: types.SimpleNamespace(size=lambda: types.SimpleNamespace(width=lambda:1280))):
            rows = [('Channel %d' % i, i) for i in range(100000)]
            view = self.gui.Browser(MagicMock(), 'Test', rows, selectable=True)
            view.refresh()
            self.assertEqual(len(view['rows'].value), 250)
            view.toggle()
            view.turn_page(1)
            view.toggle()
            self.assertEqual(view.selected, {0, 250})
            view.turn_page(-1)
            self.assertTrue(view['rows'].value[0].startswith('☑'))

    def test_empty_browser_and_back_navigation(self):
        with patch.object(self.gui, 'getDesktop', lambda _: types.SimpleNamespace(size=lambda: types.SimpleNamespace(width=lambda:1280))):
            view = self.gui.Browser(MagicMock(), 'Empty', [])
            view.refresh()
            view.action('green')
            view.turn_page(1)
            self.assertIsNone(view.row())

    def test_remote_up_down_reaches_different_rows(self):
        with patch.object(self.gui, 'getDesktop', lambda _: types.SimpleNamespace(size=lambda: types.SimpleNamespace(width=lambda:1280))):
            view = self.gui.Browser(MagicMock(), 'Navigate', [('One', 1), ('Two', 2)])
            view.refresh()
            view['keys'].actions['down']()
            self.assertEqual(view.row()[1], 2)
            view['keys'].actions['up']()
            self.assertEqual(view.row()[1], 1)

    def test_dashboard_widgets_are_above_decorative_panels(self):
        for width in (1280, 1920):
            root = ET.fromstring(self.plugin.neo_dark_skin(width))
            panels = [int(n.attrib.get('zPosition', 0)) for n in root if n.tag == 'eLabel']
            for node in root.findall('widget'):
                self.assertGreater(int(node.attrib['zPosition']), max(panels))

    def test_dashboard_reopens_with_three_choices_without_scan_download_or_large_list_load(self):
        from PiconManagerNG.runtime import Manager
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bouquets, picons = root / 'bouquets', root / 'picons'
            bouquets.mkdir(); picons.mkdir()
            (bouquets/'userbouquet.test.tv').write_text('#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a//example/live\n#DESCRIPTION Example\n')
            def manager(): return Manager(root/'data', bouquets, [str(picons)])
            manager().scan()
            with patch.object(self.plugin, 'Manager', manager), \
                    patch.object(self.plugin, 'getDesktop', lambda _: types.SimpleNamespace(size=lambda: types.SimpleNamespace(width=lambda:1280))), \
                    patch('PiconManagerNG.core.scan_bouquet_files', side_effect=AssertionError('startup scan')), \
                    patch('PiconManagerNG.network.open_source', side_effect=AssertionError('startup HTTP')):
                for _ in range(2):
                    screen = self.plugin.PiconManagerNGScreen(MagicMock())
                    for callback in screen.onLayoutFinish: callback()
                    self.assertEqual(screen['menu'].value, ['Mes picons', 'Mettre à jour', 'Réglages'])
                    self.assertEqual(screen['count_value'].value, '1')
                    self.assertEqual(screen.manager.services, [])
                    self.assertFalse(screen.busy)
                    self.assertNotIn(screen.scan, screen['keys'].actions.values())
                    screen.work = lambda task, done: done(task())
                    screen.select()  # Mes picons reuses the saved local inventory
                    self.assertEqual(screen.manager.services, [])  # satellite summary is also lazy
                    screen.session.open.assert_called_once()

    def test_satellite_browser_filter_and_multiple_update_selection_stay_local(self):
        from PiconManagerNG.runtime import Manager
        from test_groups import service
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = Manager(root/'data', root, [str(root)])
            app.services = [service(192, installed=str(root/'one.png')), service(192, 2),
                            service(3530), service(192, kind='IPTV')]
            app.inventory_loaded = True
            session = MagicMock()
            views = []
            def open_view(cls, *args, **kwargs):
                if cls is self.gui.Browser:
                    view = cls(session, *args, **kwargs)
                    view.work = lambda task, done: done(task())
                    for callback in view.onLayoutFinish: callback()
                    views.append(view)
                    return view
            session.open.side_effect = open_view
            with patch.object(self.plugin, 'Manager', return_value=app), \
                    patch.object(self.plugin, 'getDesktop', lambda _: types.SimpleNamespace(size=lambda: types.SimpleNamespace(width=lambda:1280))), \
                    patch.object(self.gui, 'getDesktop', lambda _: types.SimpleNamespace(size=lambda: types.SimpleNamespace(width=lambda:1280))), \
                    patch('PiconManagerNG.core.scan_bouquet_files', side_effect=AssertionError('unexpected scan')), \
                    patch('PiconManagerNG.network.open_source', side_effect=AssertionError('unexpected HTTP')):
                screen = self.plugin.PiconManagerNGScreen(session)
                screen.work = lambda task, done: done(task())
                screen.channels()
                group_view = views[-1]
                self.assertEqual([r[1]['key'] for r in group_view.entries], ['SAT:192', 'SAT:3530', 'IPTV'])
                with patch.object(group_view, 'work', wraps=group_view.work) as visible_work:
                    group_view['keys'].actions['ok']()
                    visible_work.assert_called_once()
                channels = views[-1]
                self.assertEqual(len(channels.entries), 2)
                channels['keys'].actions['blue']()
                self.assertEqual(len(channels.entries), 1)
                self.assertTrue(channels.entries[0][1]['installed'])
                channels['keys'].actions['blue']()
                self.assertEqual(len(channels.entries), 1)
                self.assertIsNone(channels.entries[0][1]['installed'])
                screen.check_updates()
                selection = views[-1]
                selection['keys'].actions['ok']()
                selection['keys'].actions['down']()
                selection['keys'].actions['ok']()
                with patch.object(app, 'check_updates', return_value=[]) as update, \
                        patch.object(selection, 'work', wraps=selection.work) as visible_work:
                    selection['keys'].actions['green']()
                    update.assert_called_once_with(['SAT:192', 'SAT:3530'])
                    visible_work.assert_called_once()
                for view in views:
                    view['keys'].actions['red']()
                    self.assertTrue(view.closed)

    def test_channel_rows_format_only_the_visible_page(self):
        services = [{'name': 'Test %d' % i, 'kind': 'IPTV'} for i in range(100000)]
        rows = self.gui.ChannelRows(services)
        with patch.object(self.gui.ChannelRows, 'row', wraps=self.gui.ChannelRows.row) as render:
            self.assertEqual(len(rows), 100000)
            self.assertEqual(len(rows[:250]), 250)
            self.assertEqual(render.call_count, 250)
            self.assertIs(rows[99999][1], services[-1])

    def test_closing_each_browser_preserves_native_screen_items_method(self):
        with patch.object(self.gui, 'getDesktop', lambda _: types.SimpleNamespace(size=lambda: types.SimpleNamespace(width=lambda:1920))):
            for rows in ([], [('Satellite', 192)], self.gui.ChannelRows([{'name': 'A', 'kind': 'SAT'}])):
                view = self.gui.Browser(MagicMock(), 'Exit', rows)
                self.assertTrue(callable(view.items))
                self.assertIn('rows', dict(view.items()))
                view.refresh()
                view['keys'].actions['cancel']()
                self.assertTrue(view.closed)

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PiconManagerNG import groups, catalog
from PiconManagerNG.runtime import Manager


def service(position, sid=1, kind='SAT', installed=None, name='Test'):
    ref = '1:0:1:%X:1:1:%X:0:0:0:' % (sid, (position << 16) | 0x1234)
    return {'ref': ref, 'kind': kind, 'installed': installed, 'name': name,
            'picon': ref.rstrip(':').replace(':', '_') + '.png',
            'srp_key': '%X_1_1_%X' % (sid, (position << 16) | 0x1234)}


class SatelliteGroups(unittest.TestCase):
    def test_saved_groups_open_without_reading_full_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = Manager(root/'data', root, [str(root)])
            rows = [service(192), service(3530), service(192, kind='IPTV')]
            manager._inventory_cache().save(rows, {'total': 3, 'found': 0, 'missing': 3})
            reopened = Manager(root/'data', root, [str(root)])
            with patch.object(reopened, 'load_inventory', side_effect=AssertionError('full inventory load')):
                self.assertEqual([g['key'] for g in reopened.list_groups()], ['SAT:192', 'SAT:3530', 'IPTV'])
                self.assertEqual(reopened.services, [])
                self.assertFalse(reopened.inventory_loaded)
            bad = dict(reopened.snapshot, groups=[{'key': '../broken'}])
            self.assertIsNone(groups.saved_summary(bad))

    def test_namespace_position_east_west_and_iptv_with_dvb_ids(self):
        self.assertEqual(groups.service_group(service(192)), 'SAT:192')
        self.assertEqual(groups.service_group(service(3530)), 'SAT:3530')
        self.assertEqual(groups.service_group(service(192, kind='IPTV')), 'IPTV')
        self.assertEqual(groups.service_group(service(0xFFFF, kind='CABLE')), 'CABLE')
        self.assertEqual(groups.service_group(service(0xEEEE, kind='DTT')), 'DTT')
        self.assertEqual(groups.service_group({'kind': 'SAT', 'ref': 'broken'}), 'SAT:unknown')
        self.assertEqual(groups.position_label(192), '19.2° E')
        self.assertEqual(groups.position_label(3592), '0.8° O')

    def test_local_satellite_names_and_group_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'satellites.xml'
            path.write_text('<satellites><sat name="Astra 19.2E" position="192" />'
                            '<sat name="West 7.0W" position="-70" /></satellites>')
            names = groups.satellite_names([path, Path(tmp)/'missing'])
            rows = [service(192, installed='a.png'), service(192, 2), service(3530),
                    service(192, kind='IPTV')]
            summary = groups.summarize(rows, names)
            self.assertEqual([g['key'] for g in summary], ['SAT:192', 'SAT:3530', 'IPTV'])
            self.assertEqual(summary[0]['label'], 'Astra 19.2E')
            self.assertEqual((summary[0]['total'], summary[0]['found'], summary[0]['missing']), (2, 1, 1))
            self.assertEqual(summary[1]['label'], 'West 7.0W')
            self.assertEqual(groups.select(rows, ['SAT:192']), rows[:2])
            self.assertEqual(groups.select(rows, ['SAT:3530', 'IPTV']), rows[2:])

    def test_selected_satellite_limits_catalogue_matching_and_update_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            picons = root/'picons'; picons.mkdir()
            manager = Manager(root/'data', root, [str(picons)])
            rows = [service(192), service(130, 2), service(192, 3, kind='IPTV')]
            manager.services, manager.inventory_loaded = rows, True
            manager.profile = {'style_id': 'test', 'dimensions': [400, 240], 'samples': []}
            manifest = {'schema': 2, 'style_id': 'test', 'dimensions': [400, 240],
                        'render_verified': True, 'sample_proofs': {}, 'logos': {},
                        'items': {s['picon']: {'sha256': 'a'*64,
                            'url': 'https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/picons/test.png'} for s in rows}}
            cat = {'srp': {}, 'names': {}, 'commit': 'a'*40}
            with patch.object(catalog, 'load_catalog', return_value=cat) as load, \
                    patch('PiconManagerNG.runtime.read_json', return_value=manifest):
                plan = manager.check_updates(['SAT:192'])
                self.assertEqual(load.call_args.args[0], rows[:1])
                self.assertEqual([p['name'] for p in plan], [rows[0]['picon']])
                self.assertNotIn('match', rows[1])
                self.assertNotIn('match', rows[2])
                load.reset_mock()
                self.assertEqual(manager.check_updates(['SAT:999']), [])
                load.assert_not_called()

    def test_switching_satellite_keeps_both_cached_catalogues_available_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rows in ([service(192)], [service(130)]):
                with patch.object(catalog, 'read_json', return_value={'sha': 'a'*40}), \
                        patch.object(catalog, '_stream_index', return_value={}):
                    catalog.load_catalog(rows, tmp)
            with patch.object(catalog, 'read_json', side_effect=AssertionError('unexpected HTTP')):
                for rows in ([service(192)], [service(130)]):
                    self.assertEqual(catalog.load_catalog(rows, tmp)['commit'], 'a'*40)
            self.assertEqual(len(list(Path(tmp).glob('catalog-*.json'))), 2)

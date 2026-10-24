import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from PiconManagerNG.runtime import Manager
from PiconManagerNG import catalog


class OfflineInventory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bouquets = self.root / 'bouquets'
        self.bouquets.mkdir()
        self.picons = self.root / 'picons'
        self.picons.mkdir()
        self.bouquet = self.bouquets / 'userbouquet.test.tv'
        self.bouquet.write_text('#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a//user:secret@example/live\n#DESCRIPTION Example\n')

    def manager(self):
        return Manager(self.root / 'data', self.bouquets, [str(self.picons)])

    def test_reopen_restores_summary_and_local_list_without_scan_or_network(self):
        self.manager().scan()
        # The original bouquet can disappear and the saved list still opens offline.
        self.bouquet.unlink()
        with patch('PiconManagerNG.core.scan_bouquet_files', side_effect=AssertionError('implicit scan')), \
                patch('PiconManagerNG.core.find_installed', side_effect=AssertionError('implicit inventory')), \
                patch('PiconManagerNG.network.open_source', side_effect=AssertionError('implicit network')):
            reopened = self.manager()
            self.assertEqual(reopened.counts['total'], 1)
            self.assertEqual(reopened.services, [])  # lazy, not 100,000 objects at startup
            self.assertEqual(reopened.load_inventory()[0]['name'], 'Example')
            self.assertNotIn('secret', str(reopened.services))

    def test_missing_or_corrupt_cache_does_not_trigger_an_analysis(self):
        with patch('PiconManagerNG.core.scan_bouquet_files', side_effect=AssertionError('implicit scan')):
            with self.assertRaises(ValueError):
                self.manager().load_inventory()
        app = self.manager()
        app.scan()
        (app._inventory_cache().directory / app.snapshot['file']).write_bytes(b'corrupt')
        with patch('PiconManagerNG.core.scan_bouquet_files', side_effect=AssertionError('implicit scan')), self.assertRaises(ValueError):
            self.manager().load_inventory()

    def test_empty_saved_inventory_is_reusable(self):
        self.bouquet.write_text('')
        self.manager().scan()
        with patch('PiconManagerNG.core.scan_bouquet_files', side_effect=AssertionError('implicit scan')):
            reopened = self.manager()
            self.assertEqual(reopened.counts['total'], 0)
            self.assertEqual(reopened.load_inventory(), [])
            self.assertEqual(reopened.load_inventory(), [])

    def test_radio_preference_change_needs_explicit_refresh_and_can_be_reverted(self):
        self.manager().scan()
        app = self.manager()
        with patch('PiconManagerNG.core.scan_bouquet_files', side_effect=AssertionError('implicit scan')):
            app.settings['include_radio'] = False
            app.save_settings()
            self.assertIsNone(app.snapshot)
            with self.assertRaises(ValueError):
                app.load_inventory()
            app.settings['include_radio'] = True
            app.save_settings()
            self.assertEqual(app.load_inventory()[0]['name'], 'Example')

    def test_manual_refresh_replaces_saved_state(self):
        self.manager().scan()
        self.bouquet.write_text('')
        app = self.manager()
        self.assertEqual(app.counts['total'], 1)
        app.scan()
        self.assertEqual(self.manager().counts['total'], 0)
        self.assertEqual(len(list(app._inventory_cache().directory.glob('services-*.gz'))), 1)

    def test_lyngsat_preview_downloaded_once_and_reused_after_reopen(self):
        buffer = io.BytesIO()
        Image.new('RGBA', (100, 80), (10, 20, 30, 255)).save(buffer, format='PNG')
        with patch('PiconManagerNG.network.read_source', return_value=buffer.getvalue()) as fetch:
            entry = {'url': 'https://www.lyngsat.com/logo/tv/example.png'}
            first = self.manager().lyngsat_preview(entry)
            fetch.side_effect = AssertionError('repeat preview download')
            self.assertEqual(self.manager().lyngsat_preview(entry), first)
            self.assertEqual(fetch.call_count, 1)

    def test_catalogue_is_reusable_without_age_based_download_and_falls_back_offline(self):
        services = [{'name': 'Example', 'srp_key': None}]
        cache = self.root / 'catalogue'
        with patch.object(catalog, 'read_json', return_value={'sha': 'a'*40}), \
                patch.object(catalog, '_stream_index', return_value={}), patch.object(catalog.time, 'time', return_value=0):
            catalog.load_catalog(services, cache)
        with patch.object(catalog, 'read_json', side_effect=OSError('offline')) as fetch:
            self.assertEqual(catalog.load_catalog(services, cache)['commit'], 'a'*40)
            fetch.assert_not_called()
            self.assertTrue(catalog.load_catalog(services, cache, force=True)['offline'])

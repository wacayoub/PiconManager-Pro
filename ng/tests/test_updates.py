import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch
from PIL import Image
from PiconManagerNG import updates
from PiconManagerNG.storage import atomic_json

NAME = '1_0_1_65_1_1_1E0000_0_0_0.png'
URL = 'https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/dev/piconmanager-ng-v2/ng/catalog/picons/' + NAME


class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'picons'
        self.root.mkdir()
        self.backups = Path(self.tmp.name) / 'backups'
        b = io.BytesIO()
        Image.new('RGBA', (400, 240), (200, 100, 10, 255)).save(b, format='PNG')
        self.png = b.getvalue()
        self.entry = {'name': NAME, 'url': URL, 'sha256': hashlib.sha256(self.png).hexdigest()}

    def stage(self, entries=None):
        return Path(updates.stage_plan(entries or [self.entry], self.root, self.backups, fetch=lambda _: self.png))

    def test_preview_does_not_touch_destination_then_restore(self):
        (self.root / NAME).write_bytes(b'original')
        batch = self.stage()
        self.assertEqual((self.root / NAME).read_bytes(), b'original')
        updates.apply_staged(batch, self.root)
        updates.restore_backup(batch, self.root)
        self.assertEqual((self.root / NAME).read_bytes(), b'original')

    def test_new_file_removed_on_restore(self):
        batch = self.stage()
        updates.apply_staged(batch, self.root)
        updates.restore_backup(batch, self.root)
        self.assertFalse((self.root / NAME).exists())

    def test_crash_after_replace_recovers_from_write_ahead_journal(self):
        (self.root / NAME).write_bytes(b'original')
        batch = self.stage()
        real = updates.atomic_bytes
        def crash(path, data):
            real(path, data)
            if Path(path).resolve() == (self.root / NAME).resolve():
                raise SystemExit('simulated power loss')
        with patch.object(updates, 'atomic_bytes', crash), self.assertRaises(SystemExit):
            updates.apply_staged(batch, self.root)
        self.assertEqual(json.loads((batch / 'transaction.json').read_text())['state'], 'applying')
        updates.recover_pending(self.backups, self.root)
        self.assertEqual((self.root / NAME).read_bytes(), b'original')

    def test_checksum_failure_never_applies(self):
        self.entry['sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            self.stage()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_changed_file_after_preview_is_not_overwritten(self):
        (self.root / NAME).write_bytes(b'original')
        batch = self.stage()
        (self.root / NAME).write_bytes(b'changed elsewhere')
        with self.assertRaises(ValueError):
            updates.apply_staged(batch, self.root)
        self.assertEqual((self.root / NAME).read_bytes(), b'changed elsewhere')

    def test_restore_refuses_external_edit_or_corrupt_preimage(self):
        (self.root / NAME).write_bytes(b'original')
        batch = self.stage()
        updates.apply_staged(batch, self.root)
        (batch / 'old' / NAME).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            updates.restore_backup(batch, self.root)
        self.assertEqual((self.root / NAME).read_bytes(), self.png)

    def test_wrong_root_and_unsafe_sources_rejected(self):
        batch = self.stage()
        other = Path(self.tmp.name) / 'other'
        with self.assertRaises(ValueError):
            updates.apply_staged(batch, other)
        for url in ['http://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/x',
                    'https://raw.githubusercontent.com/evil/repo/main/x',
                    URL.replace('/ng/catalog/', '/ng/%2e%2e/')]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                updates.check_url(url)

    def test_tampered_preview_rejected(self):
        batch = self.stage()
        (batch / 'new' / NAME).write_bytes(b'bad')
        with self.assertRaises(ValueError):
            updates.apply_staged(batch, self.root)

    def test_broken_png_pixel_stream_rejected(self):
        with self.assertRaises(ValueError):
            updates.verify_png(self.png[:-20])

    def test_prepared_png_is_not_downloaded_again(self):
        first = self.stage()
        (first / 'new' / NAME).unlink()  # require the persistent PNG cache, not the old preview
        fetch = Mock(side_effect=AssertionError('repeat download'))
        second = Path(updates.stage_plan([self.entry], self.root, self.backups, fetch=fetch))
        self.assertEqual((second / 'new' / NAME).read_bytes(), self.png)
        fetch.assert_not_called()

    def test_previous_version_staged_png_is_reusable_without_download(self):
        first = self.stage()
        cached = Path(self.tmp.name) / 'cache' / 'picons' / (self.entry['sha256'] + '.png')
        cached.unlink()
        fetch = Mock(side_effect=AssertionError('repeat download'))
        second = Path(updates.stage_plan([self.entry], self.root, self.backups, fetch=fetch))
        self.assertEqual((second / 'new' / NAME).read_bytes(), (first / 'new' / NAME).read_bytes())
        fetch.assert_not_called()

    def test_corrupt_cached_png_is_refetched_and_verified(self):
        first = self.stage()
        (first / 'new' / NAME).unlink()
        cached = Path(self.tmp.name) / 'cache' / 'picons' / (self.entry['sha256'] + '.png')
        cached.write_bytes(b'corrupt')
        fetch = Mock(return_value=self.png)
        updates.stage_plan([self.entry], self.root, self.backups, fetch=fetch)
        self.assertEqual(cached.read_bytes(), self.png)
        fetch.assert_called_once()

import tempfile
import unittest
from pathlib import Path
from PiconManagerNG.runtime import Manager


class Runtime(unittest.TestCase):
    def test_rescan_invalidates_matches_before_planning_new_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bouquets = root / 'bouquets'
            bouquets.mkdir()
            picons = root / 'picons'
            picons.mkdir()
            (bouquets/'userbouquet.test.tv').write_text('#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a//example/live\n#DESCRIPTION Example\n')
            app = Manager(data_dir=root/'data', bouquets=bouquets, paths=[str(picons)])
            app.catalog = {'commit': 'old', 'names': {}}
            app.scan()
            self.assertIsNone(app.catalog)
            self.assertEqual(app.counts['total'], 1)

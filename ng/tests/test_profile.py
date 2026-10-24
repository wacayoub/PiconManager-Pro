import tempfile
import unittest
from pathlib import Path
from PIL import Image
from PiconManagerNG.profile import capture_profile, validate_style


class Style(unittest.TestCase):
    def test_dimensions_alone_never_authorize_a_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sample.png'
            Image.new('RGBA', (400, 240)).save(path)
            profile = capture_profile([path])
            doc = {'style_id': profile['style_id'], 'dimensions': [400,240], 'render_verified': True}
            with self.assertRaises(ValueError):
                validate_style(doc, profile)
            doc['sample_proofs'] = {s['name']:s['sha256'] for s in profile['samples']}
            validate_style(doc, profile)
            doc['render_verified'] = False
            with self.assertRaises(ValueError):
                validate_style(doc, profile)

import tempfile
import unittest
from pathlib import Path
from PiconManagerNG.core import scan_bouquet_files, picon_candidates, service_kind, srp_key
from PiconManagerNG.catalog import read_index_lines, match_service, alias_key, materialize_manifest
from PiconManagerNG.lyngsat import _lyngsat_parse_page


class Matching(unittest.TestCase):
    def test_stream_types_and_private_ids(self):
        for kind in ('4097', '5001', '5002', '8193'):
            ref = kind + ':0:1:20:0:0:0:0:0:0:http%3a//private/live'
            self.assertEqual(service_kind(ref), 'IPTV')
            self.assertIsNone(srp_key(ref))
        self.assertEqual(service_kind('1:0:1:65:1:1:1E0000:0:0:0:http%3a//proxy'), 'IPTV')

    def test_openatv_lookup_fallbacks(self):
        names = picon_candidates('4097:0:19:0065:1:1:C01234:0:0:0:', 'Télé + HD')
        self.assertIn('1_0_1_65_1_1_C00000_0_0_0.png', names)
        self.assertIn('télé + hd.png', names)
        self.assertIn('tlplushd.png', names)

    def test_only_reachable_bouquets_lamedb_and_credential_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/'bouquets.tv').write_text('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.active.tv" ORDER BY bouquet\n')
            (p/'userbouquet.active.tv').write_text('#SERVICE 1:0:1:65:1:1:1E0000:0:0:0:\n#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a//user:secret@host/live\n#DESCRIPTION قناة العربية\n', encoding='utf8')
            (p/'userbouquet.orphan.tv').write_text('#SERVICE 1:0:1:66:1:1:1E0000:0:0:0:\n')
            (p/'lamedb').write_text('eDVB services /4/\nservices\n0065:001e0000:0001:0001:1:0\n2M\np:provider\nend\n')
            rows = scan_bouquet_files(p)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['name'], '2M')
            self.assertEqual(rows[1]['picon'], 'قناة العربية.png')
            self.assertNotIn('secret', str(rows))

    def test_ambiguity_and_exact_precedence(self):
        rows = read_index_lines(['RTL=rtl-de', 'rtl=rtl-fr'], {'rtl'}, lambda s: s.lower())
        service = {'ref': '1:0:1:65:1:1:1E0000:0:0:0:', 'name': 'RTL', 'srp_key': '65_1_1_1E0000'}
        cat = {'srp': {}, 'names': rows}
        self.assertIsNone(match_service(service, cat)['logo'])
        self.assertEqual(match_service(service, cat, {alias_key(service): 'rtl-fr'})['logo'], 'rtl-fr')
        cat['srp'][service['srp_key']] = ['rtl-de']
        self.assertEqual(match_service(service, cat, {alias_key(service): 'rtl-fr'})['logo'], 'rtl-de')

    def test_conflicting_private_target_is_not_updated(self):
        services = [{'picon': 'a.png', 'match': {'logo': 'a'}}, {'picon': 'a.png', 'match': {'logo': 'b'}}]
        doc = materialize_manifest({'logos': {'a': {'sha256':'a'}, 'b':{'sha256':'b'}}}, services)
        self.assertNotIn('a.png', doc['items'])

    def test_lyngsat_split_cells_and_entities(self):
        html = '<table><tr><td><a href="/tvchannels/ma/2M.html">2M &amp; Monde</a></td><td><img src="/logo/tv/2m.png"></td></tr></table>'
        result = _lyngsat_parse_page(html, 'https://www.lyngsat.com/logo/tvchannel/2.html')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], '2M & Monde')
        self.assertEqual(result[0]['url'], 'https://www.lyngsat.com/logo/tv/2m.png')

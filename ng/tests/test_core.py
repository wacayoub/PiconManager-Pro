import unittest
import hashlib
import struct
import tempfile
import zlib
from pathlib import Path
from PiconManagerNG.core import picon_name, srp_key, scan_bouquet_files, find_installed
from PiconManagerNG.updates import validate_manifest, plan_replacements, apply_plan, verify_png

REF='1:0:1:65:1:1:1E0000:0:0:0:'
NAME='1_0_1_65_1_1_1E0000_0_0_0.png'
URL='https://raw.githubusercontent.com/wacayoub/PiconManager-Pro/main/catalog/picons/'+NAME

class TestNG(unittest.TestCase):
    def test_srp(self):
        self.assertEqual(picon_name(REF),NAME)
        self.assertEqual(srp_key(REF),'65_1_1_1E0000')
        self.assertIsNone(picon_name('4097:0:1:0:0:0:0:0:0:0:https%3a'))
        self.assertIsNone(picon_name('1:7:1:0:0:0:0:0:0:0:'))
    def test_bouquet(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/'userbouquet.test.tv').write_text(
                '#NAME TEST\n#SERVICE '+REF+'\n#DESCRIPTION 2M\n'
                '#SERVICE '+REF+'\n#DESCRIPTION Duplicate\n'
                '#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a\n#DESCRIPTION IPTV',encoding='utf8')
            data=scan_bouquet_files(root)
            self.assertEqual(len(data),2)
            self.assertEqual(data[0]['name'],'2M')
            self.assertEqual(find_installed(data,root)['missing'],1)
    def test_manifest_requires_style(self):
        doc={'schema':1,'style_id':'choco-user','items':{NAME:{'url':URL,'sha256':'a'*64}}}
        validate_manifest(doc,'choco-user')
        with self.assertRaises(ValueError):validate_manifest(doc,'different')
        with self.assertRaises(ValueError):
            validate_manifest({'schema':1,'style_id':'choco-user',
                'items':{'../oops':{'url':URL,'sha256':'a'*64}}},'choco-user')
    def test_staged_replace_and_backup(self):
        def chunk(name,payload):
            return struct.pack('>I',len(payload))+name+payload+struct.pack('>I',zlib.crc32(name+payload)&0xffffffff)
        raw=b'\x00'+b'\x00\x00\x00\x00'*400
        fake=(b'\x89PNG\r\n\x1a\n'
              +chunk(b'IHDR',struct.pack('>IIBBBBB',400,240,8,6,0,0,0))
              +chunk(b'IDAT',zlib.compress(raw*240))
              +chunk(b'IEND',b''))
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);dest=root/'picons';dest.mkdir();backup=root/'backup'
            (dest/NAME).write_bytes(b'old')
            digest=hashlib.sha256(fake).hexdigest()
            manifest={'schema':1,'style_id':'choco-user',
                      'items':{NAME:{'url':URL,'sha256':digest}}}
            plan=plan_replacements([{'picon':NAME}],dest,manifest,'choco-user')
            self.assertEqual(len(plan),1)
            result=apply_plan(plan,dest,backup,fetch=lambda _:fake)
            self.assertEqual(result['updated'],1)
            self.assertEqual((dest/NAME).read_bytes(),fake)
            self.assertEqual((Path(result['backup'])/NAME).read_bytes(),b'old')
    def test_bad_image_rejected(self):
        with self.assertRaises(ValueError):verify_png(b'not-png')

if __name__=='__main__': unittest.main()

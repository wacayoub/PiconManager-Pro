import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from PiconManagerNG.package import validate_package, ar_members, PREFIX, version_key
from PiconManagerNG import PACKAGE_VERSION


class Packaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'tools/build_ipk.py'
        spec = importlib.util.spec_from_file_location('ng_build_ipk', path)
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def package(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            return self.builder.build(Path(tmp))

    def test_package_is_reproducible(self):
        one, two = self.package(), self.package()
        self.assertEqual(one, two)
        self.assertEqual(validate_package(one, PACKAGE_VERSION)['Architecture'], 'all')
        self.assertGreater(version_key(PACKAGE_VERSION), version_key('2.0.0-r0'))

    def test_package_never_targets_other_plugins(self):
        parts = ar_members(self.package())
        bad = self.builder.tar_gz({'usr/lib/enigma2/python/Plugins/Extensions/EPGManager/plugin.py': b'bad'})
        parts['data.tar.gz'] = bad
        with self.assertRaises(ValueError):
            validate_package(self.builder.ar(list(parts.items())), PACKAGE_VERSION)

    def test_maintainer_scripts_are_rejected(self):
        parts = ar_members(self.package())
        parts['control.tar.gz'] = self.builder.tar_gz({'control': b'Package: test\n', 'postinst': b'init 4'})
        with self.assertRaises(ValueError):
            validate_package(self.builder.ar(list(parts.items())), PACKAGE_VERSION)

    def test_wrong_release_or_truncated_package_is_rejected(self):
        blob = self.package()
        with self.assertRaises(ValueError):
            validate_package(blob, '999.0.0-r0')
        with self.assertRaises(ValueError):
            validate_package(blob[:-100], PACKAGE_VERSION)

    def test_revision_updates_are_not_ignored(self):
        self.assertGreater(version_key('2.0.0-r1'), version_key('2.0.0-r0'))

    def test_control_path_traversal_is_rejected(self):
        parts = ar_members(self.package())
        parts['control.tar.gz'] = self.builder.tar_gz({'../../../control': b'Package: test\n'})
        with self.assertRaises(ValueError):
            validate_package(self.builder.ar(list(parts.items())), PACKAGE_VERSION)

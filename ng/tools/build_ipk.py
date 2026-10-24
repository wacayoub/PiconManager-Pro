#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic portable IPK builder. No postinst, restart or external binaries."""
import argparse
import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ng/source'))
from PiconManagerNG.package import PACKAGE, PREFIX, validate_package
from PiconManagerNG import __version__


def tar_gz(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, blob in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size = len(blob)
            item.mode = 0o644
            item.mtime = 0
            item.uid = item.gid = 0
            item.uname = item.gname = 'root'
            archive.addfile(item, io.BytesIO(blob))
    return gzip.compress(stream.getvalue(), compresslevel=9, mtime=0)


def ar(files):
    data = bytearray(b'!<arch>\n')
    for name, blob in files:
        header = '%-16s%-12s%-6s%-6s%-8s%-10s`\n' % (name+'/', 0, 0, 0, '100644', len(blob))
        data.extend(header.encode('ascii'))
        data.extend(blob)
        if len(blob) % 2:
            data.extend(b'\n')
    return bytes(data)


def build(destination):
    version = __version__ + '-r0'
    files = {PREFIX + p.name: p.read_bytes().replace(b'\r\n', b'\n')
             for p in (ROOT / 'ng/source/PiconManagerNG').iterdir() if p.suffix in ('.py', '.txt') or p.name == 'LICENSE'}
    control = ('Package: %s\nVersion: %s\nArchitecture: all\nMaintainer: PiconManager Pro contributors\n'
               'Section: extra\nPriority: optional\nLicense: GPL-3.0-or-later\n'
               'Depends: enigma2, python3-core, python3-pillow\n'
               'Description: PiconManager NG - Neo Dark, selective verified picons and reversible updates\n') % (PACKAGE, version)
    blob = ar([('debian-binary', b'2.0\n'), ('control.tar.gz', tar_gz({'control': control.encode()})),
               ('data.tar.gz', tar_gz(files))])
    validate_package(blob, version)
    destination.mkdir(parents=True, exist_ok=True)
    name = PACKAGE + '_' + version + '_all.ipk'
    (destination / name).write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    (destination / (name + '.sha256')).write_text(sha + '  ' + name + '\n', encoding='ascii')
    release = {'schema': 1, 'status': 'hardware-validation-required', 'package': PACKAGE,
               'version': version, 'file': name, 'size': len(blob), 'sha256': sha,
               'url': '', 'restart': False}
    (destination / 'release.json').write_text(json.dumps(release, indent=2) + '\n', encoding='utf8')
    print(json.dumps(release, indent=2))
    return blob


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    build(args.output)

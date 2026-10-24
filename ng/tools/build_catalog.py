#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Off-receiver rendering and strict pixel calibration of an upstream catalogue.

An asset map explicitly selects upstream paths and calibration source logos.
No bouquet, service reference or original Chocholousek file is published.
"""
import argparse
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ng/source'))
from PiconManagerNG.catalog import LOGO_ID
from PiconManagerNG.network import read_source
from PiconManagerNG.storage import atomic_bytes, atomic_json
from PiconManagerNG.updates import verify_png, check_url


def render(blob, path, recipe):
    from PIL import Image, ImageOps
    if path.endswith('.svg'):
        # Block external SVG resources (including file URLs) before rasterization.
        text = blob.decode('utf8')
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
            raise ValueError('SVG entities are not permitted')
        doc = ElementTree.fromstring(text)
        for element in doc.iter():
            for key, value in element.attrib.items():
                if key.endswith('href') and not value.startswith('#'):
                    raise ValueError('External SVG resources are not permitted')
        if re.search(r'url\(\s*[\'"]?(?!#)[^)]', text, re.I):
            raise ValueError('External SVG CSS resources are not permitted')
        import cairosvg  # only on the build host/CI; never an IPK dependency
        blob = cairosvg.svg2png(bytestring=blob, output_width=1600, output_height=960)
    with Image.open(io.BytesIO(blob)) as source:
        if source.width * source.height > 16 * 1024 * 1024:
            raise ValueError('Source image too large')
        source = source.convert('RGBA')
        box = source.getchannel('A').getbbox()
        if not box:
            raise ValueError('Empty source logo')
        source = source.crop(box)
        fitted = ImageOps.contain(source, tuple(recipe['inner']), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', tuple(recipe['dimensions']), (0, 0, 0, 0))
        canvas.alpha_composite(fitted, ((canvas.width-fitted.width)//2, (canvas.height-fitted.height)//2))
        output = io.BytesIO()
        canvas.save(output, format='PNG')
    return output.getvalue()


def fetch_logo(commit, path):
    if not path.startswith('build-source/logos/') or '..' in path.split('/') or not path.endswith(('.svg', '.png')):
        raise ValueError('Expected an explicit picons/picons logo source path')
    return read_source('https://raw.githubusercontent.com/picons/picons/' + commit + '/' + path, 8*1024*1024)


def build(profile, mapping, recipe, originals, output, base_url):
    from PIL import Image
    commit = mapping.get('upstream_commit', '')
    if not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Pin upstream_commit to a full Git SHA')
    if recipe.get('dimensions') != profile.get('dimensions'):
        raise ValueError('Recipe dimensions differ from original profile')
    if any(not isinstance(n, int) or n <= 0 for n in recipe.get('inner', [])) or len(recipe.get('inner', [])) != 2:
        raise ValueError('Missing calibrated inner box')
    if any(a > b for a, b in zip(recipe['inner'], recipe['dimensions'])):
        raise ValueError('Inner box exceeds canvas')
    proofs, comparisons = {}, []
    sources = mapping.get('calibration', {})
    if len(profile.get('samples', [])) < 3:
        raise ValueError('At least three original samples are required')
    for sample in profile['samples']:
        name = sample['name']
        original = (originals / name).read_bytes()
        if hashlib.sha256(original).hexdigest() != sample['sha256']:
            raise ValueError('Original sample hash differs: ' + name)
        source_path = sources.get(name)
        if not source_path:
            raise ValueError('Missing calibration source for ' + name)
        candidate = render(fetch_logo(commit, source_path), source_path, recipe)
        with Image.open(io.BytesIO(candidate)) as new, Image.open(io.BytesIO(original)) as old:
            equal = new.size == old.size and new.convert('RGBA').tobytes() == old.convert('RGBA').tobytes()
        comparisons.append({'sample': name, 'pixels_identical': equal})
        if equal:
            proofs[name] = sample['sha256']
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / 'calibration-report.json', {'checks': comparisons, 'upstream_commit': commit})
    if not all(row['pixels_identical'] for row in comparisons):
        raise ValueError('Exact calibration failed. No public catalogue was generated; originals remain unchanged.')
    logos = {}
    for logo_id, source_path in mapping.get('logos', {}).items():
        if not LOGO_ID.fullmatch(logo_id):
            raise ValueError('Invalid logo ID')
        source = fetch_logo(commit, source_path)
        png = render(source, source_path, recipe)
        verify_png(png, profile['dimensions'])
        url = base_url.rstrip('/') + '/picons/' + logo_id + '.png'
        check_url(url)
        atomic_bytes(output / 'picons' / (logo_id + '.png'), png)
        logos[logo_id] = {'url': url, 'sha256': hashlib.sha256(png).hexdigest(), 'size': len(png),
                          'source': {'repository': 'picons/picons', 'commit': commit, 'path': source_path,
                                     'sha256': hashlib.sha256(source).hexdigest(), 'license': 'GPL-3.0'}}
    manifest = {'schema': 2, 'style_id': profile['style_id'], 'dimensions': profile['dimensions'],
                'sample_proofs': proofs, 'render_verified': True, 'items': {}, 'logos': logos,
                'generated_at': datetime.now(timezone.utc).isoformat(), 'upstream_commit': commit}
    atomic_json(output / 'manifest.json', manifest)
    atomic_bytes(output / 'NOTICE.txt', b'Artwork and indexes: picons/picons (GPL-3.0).\nhttps://github.com/picons/picons\nLogos retain their respective trademark rights.\n')
    atomic_bytes(output / 'LICENSE', read_source('https://raw.githubusercontent.com/picons/picons/' + commit + '/LICENSE', 65536))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'mapping', 'recipe', 'originals', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--base-url', required=True)
    args = parser.parse_args()
    try:
        manifest = build(*(json.loads(getattr(args, n).read_text(encoding='utf8')) for n in ('profile', 'mapping', 'recipe')),
                         args.originals, args.output, args.base_url)
        print('%d verified PNGs prepared' % len(manifest['logos']))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')

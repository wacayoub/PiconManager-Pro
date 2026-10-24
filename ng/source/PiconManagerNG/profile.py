# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture current pixel evidence. Never infer an exact style from dimensions."""
import hashlib
import json
from pathlib import Path


def inspect_samples(paths):
    from PIL import Image
    result = []
    for path in paths:
        path = Path(path)
        with Image.open(path) as image:
            image.load()
            rgba = image.convert('RGBA')
            alpha = rgba.getchannel('A')
            result.append({'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'dimensions': list(image.size), 'alpha_bbox': alpha.getbbox(),
                           'transparent': alpha.getextrema()[0] == 0})
    return result


def capture_profile(sample_paths):
    samples = inspect_samples(sample_paths)
    if not samples or len({tuple(s['dimensions']) for s in samples}) != 1:
        raise ValueError('Échantillons absents ou dimensions incompatibles')
    fingerprint = hashlib.sha256(json.dumps(samples, sort_keys=True).encode()).hexdigest()[:20]
    return {'schema': 1, 'style_id': 'chocholousek-' + fingerprint,
            'dimensions': samples[0]['dimensions'], 'samples': samples,
            'render_verified': False,
            'note': 'Originaux conservés. La recette de rendu doit reproduire les échantillons avant diffusion.'}


def validate_style(manifest, profile):
    if not profile or manifest.get('style_id') != profile.get('style_id'):
        raise ValueError('Le catalogue ne correspond pas aux originaux Chocholousek')
    if tuple(manifest.get('dimensions', ())) != tuple(profile.get('dimensions', ())):
        raise ValueError('Dimensions différentes du profil Chocholousek')
    if manifest.get('sample_proofs') != {s['name']: s['sha256'] for s in profile['samples']}:
        raise ValueError('Calibration Chocholousek non vérifiée')
    if not manifest.get('render_verified'):
        raise ValueError('Rendu exact des picons pas encore validé')

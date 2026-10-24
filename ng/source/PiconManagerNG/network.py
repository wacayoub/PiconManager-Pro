# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded HTTPS reads from explicitly supported upstreams."""
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HOSTS = {'api.github.com', 'raw.githubusercontent.com', 'www.lyngsat.com', 'lyngsat.com'}


def check_source(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Source HTTPS non autorisée')
    if parsed.hostname == 'api.github.com' and not parsed.path.startswith(('/repos/picons/picons/', '/repos/wacayoub/PiconManager-Pro/')):
        raise ValueError('Dépôt non autorisé')
    if parsed.hostname == 'raw.githubusercontent.com' and not parsed.path.startswith(('/picons/picons/', '/wacayoub/PiconManager-Pro/')):
        raise ValueError('Dépôt non autorisé')


def open_source(url):
    check_source(url)
    request = Request(url, headers={'User-Agent': 'PiconManagerNG/2.0', 'Accept': '*/*',
                                   'Referer': 'https://www.lyngsat.com/'})
    response = urlopen(request, timeout=15)
    try:
        check_source(response.geturl())
    except Exception:
        response.close()
        raise
    return response


def read_source(url, maximum=4 * 1024 * 1024):
    with open_source(url) as response:
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError('Réponse trop volumineuse')
    return data


def read_json(url, maximum=8 * 1024 * 1024):
    return json.loads(read_source(url, maximum).decode('utf8'))

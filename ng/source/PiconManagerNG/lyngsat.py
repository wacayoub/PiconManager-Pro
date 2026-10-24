# SPDX-License-Identifier: GPL-3.0-or-later
"""LyngSat 1.5.1 parser, preserved with split-cell fallback."""
import re
from html.parser import HTMLParser
from html import unescape
from urllib.parse import urljoin
from .core import clean_name
from .catalog import name_key
from .network import read_source
from .storage import atomic_json
from pathlib import Path
import json
import time

def compact_key(value):
    return re.sub(r'[^\w]+', '', clean_name(value).casefold())

class _LyngSatLogoPageParser(HTMLParser):
    """Extract LyngSat channel-name -> logo URL pairs.

    LyngSat's current logo pages no longer guarantee that the channel anchor and
    logo image live in the same <td>.  The old 1.5.0 parser therefore returned
    zero rows on the current layout.  This parser records channel anchors and
    logo images at row/cell level and pairs them when possible.  A second,
    document-order regex pass in _lyngsat_parse_page covers split-cell layouts.
    """
    def __init__(self, page_url):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.page_url = page_url
        self.rows = []
        self.in_a = False
        self.anchor_buf = []
        self.anchor_href = ""
        self.in_td = 0
        self.in_tr = 0
        self.cell_channels = []
        self.cell_logos = []
        self.row_channels = []
        self.row_logos = []

    @staticmethod
    def _is_channel_href(href):
        h = (href or "").lower()
        return "/tvchannels/" in h or h.startswith("tvchannels/")

    @staticmethod
    def _is_logo_src(src):
        s = (src or "").lower()
        return "/logo/tv/" in s and re.search(r"\.(?:png|svg|webp)(?:\?|$)", s, re.I)

    def _emit_pairs(self, channels, logos):
        if not channels or not logos:
            return
        if len(channels) == len(logos):
            pairs = zip(channels, logos)
        elif len(channels) == 1:
            pairs = [(channels[0], logos[0])]
        elif len(logos) == 1:
            pairs = [(channels[0], logos[0])]
        else:
            pairs = zip(channels[:min(len(channels), len(logos))], logos[:min(len(channels), len(logos))])
        for name, url in pairs:
            if name and url:
                self.rows.append((name, url, self.page_url))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs or [])
        if tag == "tr":
            if self.in_tr == 0:
                self.row_channels = []
                self.row_logos = []
            self.in_tr += 1
        elif tag == "td":
            if self.in_td == 0:
                self.cell_channels = []
                self.cell_logos = []
            self.in_td += 1
        elif tag == "a":
            self.in_a = True
            self.anchor_buf = []
            self.anchor_href = attrs.get("href") or ""
        elif tag == "img":
            src = attrs.get("src") or ""
            if self._is_logo_src(src):
                url = urljoin(self.page_url, src)
                if self.in_td:
                    self.cell_logos.append(url)
                if self.in_tr:
                    self.row_logos.append(url)
                alt = clean_name(attrs.get("alt") or attrs.get("title") or "")
                if alt and alt.lower() not in ("image", "lyngsat", "lyngsat logo"):
                    self.rows.append((alt, url, self.page_url))

    def handle_data(self, data):
        if self.in_a and data:
            self.anchor_buf.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "a":
            name = clean_name("".join(self.anchor_buf))
            href = self.anchor_href
            self.in_a = False
            self.anchor_buf = []
            self.anchor_href = ""
            if name and self._is_channel_href(href):
                if self.in_td:
                    self.cell_channels.append(name)
                if self.in_tr:
                    self.row_channels.append(name)
        elif tag == "td" and self.in_td:
            self.in_td -= 1
            if self.in_td == 0:
                self._emit_pairs(self.cell_channels, self.cell_logos)
                self.cell_channels = []
                self.cell_logos = []
        elif tag == "tr" and self.in_tr:
            self.in_tr -= 1
            if self.in_tr == 0:
                self._emit_pairs(self.row_channels, self.row_logos)
                self.row_channels = []
                self.row_logos = []


def _lyngsat_regex_pairs(html, page_url):
    """Fallback for the current split-cell LyngSat layout.

    A channel entry is a /tvchannels/ anchor followed shortly by its /logo/tv/
    image.  Header/news blocks commonly put the image *before* the channel link,
    so this forward-only pairing also avoids most navigation/news false matches.
    """
    text = html or ""
    channel_re = re.compile(
        r'<a\b[^>]*href=["\']([^"\']*(?:/|^)tvchannels/[^"\']+)["\'][^>]*>(.*?)</a>',
        re.I | re.S,
    )
    logo_re = re.compile(
        r'<img\b[^>]*src=["\']([^"\']*/logo/tv/[^"\']+\.(?:png|svg|webp)(?:\?[^"\']*)?)["\'][^>]*>',
        re.I | re.S,
    )
    anchors = list(channel_re.finditer(text))
    out = []
    for i, match in enumerate(anchors):
        raw_name = re.sub(r"<[^>]+>", " ", match.group(2) or "")
        name = clean_name(unescape(re.sub(r"\s+", " ", raw_name)))
        if not name:
            continue
        # Do not let one channel consume a logo belonging to a later channel.
        limit = anchors[i + 1].start() if i + 1 < len(anchors) else min(len(text), match.end() + 3000)
        # Current cards are compact; cap the forward search to avoid unrelated art.
        limit = min(limit, match.end() + 2200)
        logo = logo_re.search(text, match.end(), limit)
        if not logo:
            continue
        out.append((name, urljoin(page_url, logo.group(1)), page_url))
    return out


def _lyngsat_parse_page(html, page_url):
    parser = _LyngSatLogoPageParser(page_url)
    parser.feed(html or "")
    parser.close()
    rows = list(parser.rows)
    # Always merge the document-order pass: it is what fixes the 2026 split-cell
    # layout while the HTMLParser pass remains useful for older/simpler layouts.
    rows.extend(_lyngsat_regex_pairs(html or "", page_url))
    out = []
    seen = set()
    for name, url, page in rows:
        key = (compact_key(name), url)
        if not key[0] or key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "url": url, "page": page})
    return out

def _lyngsat_letter(name):
    value = clean_name(name)
    try:
        import unicodedata
        value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    except Exception:
        pass
    for c in value.upper():
        if "A" <= c <= "Z":
            return c
        if "1" <= c <= "9":
            return c
        if c == "0":
            # LyngSat has numeric pages 1..9 only; 0-prefixed names are uncommon.
            return "1"
    return ""


def lookup_services(services, cache_dir, force=False):
    """Only request necessary initial letters; cache the compact selected results."""
    cache = Path(cache_dir) / 'lyngsat.json'
    try:
        state = json.loads(cache.read_text(encoding='utf8'))
    except (OSError, ValueError):
        state = {'schema': 2, 'letters': {}}
    wanted = {name_key(s.get('name', '')) for s in services if s.get('name')}
    letters = sorted({_lyngsat_letter(s.get('name', '')) for s in services} - {''})
    rows, errors, indexed = {}, [], 0
    for letter in letters:
        page = 'https://www.lyngsat.com/logo/tvchannel/' + letter + '.html'
        prior = state['letters'].get(letter, {})
        if force or not prior.get('entries'):
            try:
                html = read_source(page).decode('utf8', 'replace')
                parsed = _lyngsat_parse_page(html, page)
                if not parsed:
                    raise ValueError('Page sans logo (ou accès refusé)')
                prior = {'at': time.time(), 'entries': parsed}
                state['letters'][letter] = prior
                atomic_json(cache, state)
            except Exception:
                errors.append(letter)
        indexed += len(prior.get('entries', []))
        for item in prior.get('entries', []):
            key = name_key(item['name'])
            if key in wanted:
                rows.setdefault(key, {})[item['url']] = item
    return {'indexed': indexed, 'matches': {k: list(v.values()) for k, v in rows.items()},
            'failed_letters': errors}



# SPDX-License-Identifier: GPL-3.0-or-later
"""Local satellite groups. IPTV keeps its own group even with borrowed DVB IDs."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ALL = 'ALL'


def saved_summary(snapshot):
    rows = (snapshot or {}).get('groups')
    if not isinstance(rows, list):
        return None
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('key'), str) or
                not re.fullmatch(r'SAT:(?:[1-9][0-9]{0,3}|unknown)|IPTV|CABLE|DTT|OTHER', row['key']) or
                row['key'] in seen or not isinstance(row.get('label'), str) or
                not all(isinstance(row.get(k), int) and row[k] >= 0 for k in ('total', 'found', 'missing')) or
                row['found'] + row['missing'] != row['total']):
            return None
        seen.add(row['key'])
    if sum(row['total'] for row in rows) != snapshot.get('rows'):
        return None
    return [dict(row) for row in rows]


def service_group(service):
    kind = service.get('kind')
    if kind != 'SAT':
        return kind if kind in ('IPTV', 'CABLE', 'DTT') else 'OTHER'
    try:
        # Low namespace bits identify a transponder, not a different satellite.
        position = int(service['ref'].split(':')[6], 16) >> 16
        if 0 < position < 3600:
            return 'SAT:%d' % position
    except (KeyError, IndexError, ValueError, TypeError):
        pass
    return 'SAT:unknown'


def position_label(position):
    value = position if position <= 1800 else 3600 - position
    return '%d.%d° %s' % (value // 10, value % 10, 'E' if position <= 1800 else 'O')


def satellite_names(paths):
    """Read the receiver's local position names, without tuner or network access."""
    names = {}
    for path in paths:
        try:
            for _, node in ET.iterparse(Path(path), events=('end',)):
                if node.tag == 'sat':
                    position = int(node.attrib['position']) % 3600
                    name = node.attrib.get('name', '').strip()
                    if position and name:
                        names.setdefault(position, name)
                node.clear()
        except (OSError, ET.ParseError, ValueError, KeyError):
            continue
    return names


def summarize(services, names=None):
    names = names or {}
    groups = {}
    labels = {'IPTV': 'IPTV', 'CABLE': 'Câble', 'DTT': 'TNT',
              'OTHER': 'Autres', 'SAT:unknown': 'Satellite non identifié'}
    for service in services:
        key = service_group(service)
        if key not in groups:
            if key.startswith('SAT:') and key != 'SAT:unknown':
                position = int(key[4:])
                label = names.get(position, position_label(position))
                order = (0 if position <= 1800 else 1, position if position <= 1800 else 3600-position)
            else:
                label, order = labels[key], (2, list(labels).index(key))
            groups[key] = {'key': key, 'label': label, 'total': 0, 'found': 0, 'missing': 0, '_order': order}
        group = groups[key]
        group['total'] += 1
        group['found' if service.get('installed') else 'missing'] += 1
    result = sorted(groups.values(), key=lambda g: g['_order'])
    for group in result:
        del group['_order']
    return result


def select(services, keys=None):
    if keys is None or ALL in keys:
        return services
    allowed = set(keys)
    return [service for service in services if service_group(service) in allowed]

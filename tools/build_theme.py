#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Build a freedesktop icon theme from the reviewed catalog, never live settings."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
NAME = 'MonochromeIcons'
CATEGORIES = {
    'menu-accessories': 'applications-accessories',
    'menu-development': 'applications-development',
    'menu-education': 'applications-education',
    'menu-games': 'applications-games',
    'menu-graphics': 'applications-graphics',
    'menu-internet': 'applications-internet',
    'menu-multimedia': 'applications-multimedia',
    'menu-office': 'applications-office',
    'menu-science': 'applications-science',
    'menu-system': 'applications-system',
    'menu-settings': 'preferences-system',
}


def build(cleared_only=False):
    catalog = json.loads((ROOT/'assets.json').read_text())
    selected = [a for a in catalog['assets'] if not cleared_only or a['review_status']=='cleared']
    if not selected:
        raise ValueError('No cleared artwork is available; do not publish the pending draft.')
    target = ROOT/'theme'/NAME
    expected = {}

    def add(relative, data, key):
        previous = expected.get(relative)
        checksum = hashlib.sha256(data).hexdigest()
        if previous and previous['sha256'] != checksum:
            raise ValueError('Conflicting icon alias: ' + relative)
        expected[relative] = {'file': 'theme/'+NAME+'/'+relative, 'sha256': checksum, 'asset_key': key}
        path = target/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ValueError('Refusing to overwrite a symlink: ' + relative)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)

    for asset in selected:
        key = asset['key']
        if not re.fullmatch(r'[A-Za-z0-9._-]+', key):
            raise ValueError('Unsafe asset name')
        source = ROOT/asset['file']
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != asset['sha256']:
            raise ValueError('Artwork checksum mismatch: ' + key)
        if 'weather_assignment' in asset:
            continue  # These are rendered into the plugin-specific PNG bundle.
        add('apps/scalable/monochrome-'+key+'.svg', data, key)
        add('apps/scalable/'+key+'.svg', data, key)
        assignment = asset.get('theme_assignment', asset.get('menu_assignment', {}))
        if assignment.get('icon_name'):
            add('apps/scalable/'+assignment['icon_name']+'.svg', data, key)
        if key == 'plank-applications':
            add('apps/scalable/gnome-applications.svg', data, key)
        if key in CATEGORIES:
            add('categories/scalable/'+CATEGORIES[key]+'.svg', data, key)
    index = '''[Icon Theme]
Name=Monochrome Icons
Comment=White artwork on black faces; WhiteSur-compatible application and category overlay.
Inherits=WhiteSur-dark,hicolor
Directories=apps/scalable,categories/scalable

[apps/scalable]
Size=64
Type=Scalable
Context=Applications
MinSize=16
MaxSize=512

[categories/scalable]
Size=64
Type=Scalable
Context=Categories
MinSize=16
MaxSize=512
'''
    add('index.theme', index.encode(), None)
    actual = {str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()}
    if actual != set(expected):
        # Do not remove artwork blindly when switching between draft/release builds.
        raise ValueError('Theme contains stale or unlisted files; use a fresh build directory.')
    package = {'name': NAME, 'kind': 'WhiteSur-compatible icon-theme overlay',
               'inherits': ['WhiteSur-dark','hicolor'], 'selection': 'cleared-only' if cleared_only else 'draft',
               'files': list(expected.values())}
    (ROOT/'theme-files.json').write_text(json.dumps(package, indent=2)+'\n')
    print(f'Built {NAME}: {len(selected)} catalog entries, {len(expected)} theme files; no desktop changes.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cleared-only', action='store_true')
    args=parser.parse_args()
    build(args.cleared_only)

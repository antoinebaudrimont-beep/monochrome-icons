#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Build a freedesktop icon theme from the reviewed catalog, never live settings."""
import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NAME = 'MonochromeIcons'
SIZES = (16, 22, 24, 32, 40, 48, 64, 96, 128, 256)
SAFE = re.compile(r'[A-Za-z0-9._-]+')
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


def icon_names(catalog, selected):
    """One portable name has one drawing; shared application names stay shared."""
    names = {}
    keys = {a['key'] for a in selected if 'weather_assignment' not in a}
    def add(context, name, key):
        if not SAFE.fullmatch(name) or name in {'.','..'}:
            raise ValueError('Unsafe icon name: ' + name)
        pair = context, name
        if pair in names and names[pair] != key:
            raise ValueError('Conflicting icon alias: ' + name)
        names[pair] = key
    for asset in selected:
        key = asset['key']
        if not SAFE.fullmatch(key) or key in {'.','..'}:
            raise ValueError('Unsafe asset name')
        if 'weather_assignment' in asset:
            continue
        add('apps', 'monochrome-'+key, key)
        add('apps', key, key)
        assignment = asset.get('theme_assignment', asset.get('menu_assignment', {}))
        if assignment.get('icon_name'):
            add('apps', assignment['icon_name'], key)
        if key == 'plank-applications':
            add('apps', 'gnome-applications', key)
        if key in CATEGORIES:
            add('categories', CATEGORIES[key], key)
    for alias in catalog.get('native_aliases', []):
        key = alias['asset_key']
        if key not in keys:
            raise ValueError('Native alias references excluded artwork: ' + alias['name'])
        add('apps', alias['name'], key)
    return names


def preflight(target, manifest):
    """Reject user edits/unlisted files before writing; only retire managed files."""
    actual = {p for p in target.rglob('*') if p.is_file() or p.is_symlink()}
    old = set()
    if manifest.exists():
        package = json.loads(manifest.read_text())
        if package['name'] != NAME:
            raise ValueError('Unexpected previous theme name')
        for entry in package['files']:
            path = ROOT/entry['file']
            if not path.is_relative_to(target) or '..' in Path(entry['file']).parts:
                raise ValueError('Unsafe previous manifest path')
            old.add(path)
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError('Previous managed theme file was edited: ' + entry['file'])
    if actual != old or any(p.is_symlink() for p in target.rglob('*')):
        raise ValueError('Theme contains unlisted files or symlinks; refusing to rebuild')
    return old


def build(cleared_only=False):
    # Rendering is a development dependency, not an installation dependency.
    from make_previews import render
    catalog = json.loads((ROOT/'assets.json').read_text())
    selected = [a for a in catalog['assets'] if not cleared_only or a['review_status']=='cleared']
    if not selected:
        raise ValueError('No cleared artwork is available; do not publish the pending draft.')
    target = ROOT/'theme'/NAME
    manifest = ROOT/'theme-files.json'
    old = preflight(target, manifest)
    names = icon_names(catalog, selected)
    by_key = {a['key']:a for a in selected}
    images = {}
    for key in sorted(set(names.values())):
        asset = by_key[key]
        source = ROOT/asset['file']
        if source.parent != ROOT/'icons' or source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('Artwork checksum/path mismatch: ' + key)
        for size in SIZES:
            image = render(source, size)
            if image.size != (size,size):
                raise ValueError('Artwork must render square: ' + key)
            buffer = BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            images[key,size] = buffer.getvalue()
    expected, contents = {}, {}
    for (context,name), key in sorted(names.items()):
        for size in SIZES:
            relative = f'{context}/{size}/{name}.png'
            data = images[key,size]
            contents[relative] = data
            expected[relative] = {'file': 'theme/'+NAME+'/'+relative,
                'sha256': hashlib.sha256(data).hexdigest(), 'asset_key': key,
                'source_sha256': by_key[key]['sha256'], 'format': 'png', 'size': size}
    folders = [f'{context}/{size}' for context in ('apps','categories') for size in SIZES]
    index = ('[Icon Theme]\nName=Monochrome Icons\n'
        'Comment=White drawings on black faces; GTK and Qt compatible native-name overlay.\n'
        'Inherits=WhiteSur-dark,hicolor\nDirectories='+','.join(folders)+'\n')
    for folder in folders:
        context,size = folder.split('/')
        index += f'\n[{folder}]\nSize={size}\nType=Fixed\nContext={"Applications" if context=="apps" else "Categories"}\n'
    contents['index.theme'] = index.encode()
    expected['index.theme'] = {'file':'theme/'+NAME+'/index.theme',
        'sha256':hashlib.sha256(index.encode()).hexdigest(), 'asset_key':None, 'format':'index'}
    # All input validation/rendering completes before changing the built package.
    for relative,data in contents.items():
        path = target/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    keep = {target/relative for relative in expected}
    for path in old-keep:
        path.unlink()  # Only unedited files listed by the previous build manifest.
    for path in sorted(target.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    package = {'name': NAME, 'version':catalog['version'], 'kind': 'WhiteSur-compatible icon-theme overlay',
               'inherits': ['WhiteSur-dark','hicolor'], 'selection': 'cleared-only' if cleared_only else 'draft',
               'runtime_format':'png', 'sizes':list(SIZES), 'native_aliases':catalog.get('native_aliases',[]),
               'files': list(expected.values())}
    manifest.write_text(json.dumps(package, indent=2)+'\n')
    print(f'Built {NAME}: {len(selected)} catalog entries, {len(expected)} theme files; no desktop changes.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cleared-only', action='store_true')
    args=parser.parse_args()
    build(args.cleared_only)

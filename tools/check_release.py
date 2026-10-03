#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Check the clean export; strict mode also enforces release-review gates."""

import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SVG_NS = "http://www.w3.org/2000/svg"
# Assemble these tokens so the scanner's own source does not match its rules.
PRIVATE = re.compile("|".join([
    "/" + "/".join(("home", r"[^/\s]+")),
    "/" + "/".join(("Users", r"[^/\s]+")),
    "file:" + "//",
    "-".join(("chatgpt", "projects")),
    re.escape("/".join((".local", "state", "plank-icon-backups"))),
]))


def check(draft=False):
    errors = []
    catalog = json.loads((ROOT / "assets.json").read_text())
    assets = catalog["assets"]
    expected = set()
    names = set()
    for asset in assets:
        path = ROOT / asset["file"]
        if path.parent != ROOT / "icons" or path.suffix != ".svg":
            errors.append(f"Invalid icon path: {asset['file']}")
            continue
        if asset["key"] in names:
            errors.append(f"Duplicate icon key: {asset['key']}")
        names.add(asset["key"])
        expected.add(path)
        if not path.is_file() or path.is_symlink():
            errors.append(f"Missing icon or symlink: {asset['file']}")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != asset["sha256"]:
            errors.append(f"Checksum mismatch: {asset['file']}")
        try:
            svg = ET.fromstring(data)
            if svg.tag != f"{{{SVG_NS}}}svg":
                errors.append(f"Not an SVG: {asset['file']}")
            for node in svg.iter():
                if node.tag.rsplit("}", 1)[-1] in {"script", "foreignObject"}:
                    errors.append(f"Executable SVG content: {asset['file']}")
                for key, value in node.attrib.items():
                    local = key.rsplit("}", 1)[-1]
                    if local.startswith("on"):
                        errors.append(f"SVG event handler: {asset['file']}")
                    if local == "href" and not value.startswith(("#", "data:image/")):
                        errors.append(f"External SVG reference: {asset['file']}")
        except ET.ParseError as exc:
            errors.append(f"Invalid SVG: {asset['file']}: {exc}")
        if not draft and asset["review_status"] != "cleared":
            errors.append(f"Rights review pending: {asset['name']}")
        if not draft:
            if not asset.get('license') or not asset.get('copyright') or not asset.get('source', {}).get('license'):
                errors.append('Missing license or credit: ' + asset['key'])
            for notice in asset.get('source', {}).get('notices', []):
                location = ROOT / notice
                if '..' in Path(notice).parts or not location.is_relative_to(ROOT) or not location.is_file():
                    errors.append('Missing or unsafe notice: ' + asset['key'])

    if set((ROOT / "icons").glob("*.svg")) != expected:
        errors.append("Icon files differ from the catalog")
    by_key = {a['key']:a for a in assets}
    native_names = set()
    for alias in catalog.get('native_aliases', []):
        name,key = alias['name'],alias['asset_key']
        if (not re.fullmatch(r'[A-Za-z0-9._-]+',name) or name in {'.','..'} or
                re.fullmatch(r'brave-[a-p]{32}-.+',name) or name in native_names):
            errors.append('Invalid, private or duplicate native alias: '+name)
        native_names.add(name)
        if key not in by_key or by_key[key]['review_status']!='cleared' or 'weather_assignment' in by_key[key]:
            errors.append('Native alias uses excluded artwork: '+name)
    if set(by_key) & {a['key'] for a in catalog.get('omitted',[])}:
        errors.append('Omitted artwork appears in the distributed catalog')
    bundle_expected = set()
    for bundle in catalog.get('bundles', []):
        if bundle['type'] != 'xfce-weather-icon-theme' or bundle['sizes'] != [22,48,128]:
            errors.append('Unexpected companion bundle')
            continue
        conditions = {a['weather_assignment']['condition'] for a in assets
                      if a['key'] in bundle['condition_assets'] and 'weather_assignment' in a}
        if len(conditions) != 38 or len(bundle['condition_assets']) != 38:
            errors.append('Weather condition catalog is incomplete')
        allowed = {'weather/theme.info'} | {
            f'weather/{size}/{name}.png' for size in bundle['sizes'] for name in conditions}
        if {f['file'] for f in bundle['files']} != allowed:
            errors.append('Weather PNG inventory is incomplete')
        for entry in bundle['files']:
            if entry['file'] not in allowed:
                errors.append('Invalid bundle path: ' + entry['file'])
                continue
            path = ROOT / entry['file']
            bundle_expected.add(path)
            if not path.is_file() or path.is_symlink():
                errors.append('Missing bundle file: ' + entry['file'])
                continue
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                errors.append('Bundle checksum mismatch: ' + entry['file'])
            if path.suffix == '.png':
                size = int(path.parent.name)
                if (len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n' or
                        data[12:16] != b'IHDR' or struct.unpack('>II', data[16:24]) != (size,size)):
                    errors.append('Invalid PNG dimensions: ' + entry['file'])
        if not draft and bundle['review_status'] != 'cleared':
            errors.append('Companion bundle rights review pending: ' + bundle['key'])
    if {p for p in (ROOT/'weather').rglob('*') if p.is_file()} != bundle_expected:
        errors.append('Weather files differ from catalog')
    preview_expected = set()
    for entry in catalog.get('previews', []):
        path = ROOT / entry['file']
        if path.parent != ROOT/'previews' or path.suffix != '.png':
            errors.append('Invalid preview path: ' + entry['file'])
            continue
        preview_expected.add(path)
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            errors.append('Missing or modified preview: ' + entry['file'])
    if set((ROOT/'previews').glob('*.png')) != preview_expected:
        errors.append('Preview files differ from catalog')
    theme_manifest=ROOT/'theme-files.json'
    if theme_manifest.exists():
        package=json.loads(theme_manifest.read_text())
        theme_root=ROOT/'theme'/package['name']
        theme_expected=set()
        by_key={a['key']:a for a in assets}
        if package.get('version')!=catalog['version'] or package.get('native_aliases')!=catalog.get('native_aliases'):
            errors.append('Theme version/native aliases differ from catalog')
        if package.get('runtime_format')!='png' or package.get('sizes')!=[16,22,24,32,40,48,64,96,128,256]:
            errors.append('Unexpected runtime format or sizes')
        entries={entry['file']:entry for entry in package['files']}
        if len(entries)!=len(package['files']):
            errors.append('Duplicate theme manifest path')
        for entry in package['files']:
            path=ROOT/entry['file']
            if not path.is_relative_to(theme_root) or '..' in Path(entry['file']).parts:
                errors.append('Invalid theme package path: '+entry['file'])
                continue
            theme_expected.add(path)
            if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
                errors.append('Missing or modified theme file: '+entry['file'])
                continue
            key=entry.get('asset_key')
            if key is not None:
                if (key not in by_key or entry.get('source_sha256')!=by_key[key]['sha256'] or
                        'weather_assignment' in by_key[key] or by_key[key]['review_status']!='cleared'):
                    errors.append('Theme source differs from cleared catalog artwork: '+entry['file'])
                size=entry.get('size')
                data=path.read_bytes()
                if (entry.get('format')!='png' or path.suffix!='.png' or str(size)!=path.parent.name or
                        size not in package.get('sizes',[]) or len(data)<33 or
                        data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR' or
                        struct.unpack('>II',data[16:24])!=(size,size)):
                    errors.append('Invalid runtime PNG: '+entry['file'])
            elif path!=theme_root/'index.theme' or entry.get('format')!='index':
                errors.append('Unattributed theme file: '+entry['file'])
        for alias in catalog.get('native_aliases',[]):
            for size in package.get('sizes',[]):
                filename=f"theme/{package['name']}/apps/{size}/{alias['name']}.png"
                if entries.get(filename,{}).get('asset_key')!=alias['asset_key']:
                    errors.append('Native alias is missing or uses wrong drawing: '+filename)
        actual={p for p in (ROOT/'theme').rglob('*') if p.is_file()}
        if actual!=theme_expected:errors.append('Theme files differ from theme manifest')
        index=configparser.ConfigParser()
        try:
            index.read(theme_root/'index.theme')
            if index['Icon Theme']['Inherits'].split(',')!=package['inherits']:
                errors.append('Theme inheritance differs from manifest')
            for folder in index['Icon Theme']['Directories'].split(','):
                section=index[folder]
                if (section['Type']!='Fixed' or not (theme_root/folder).is_dir() or
                        int(section['Size']) not in package.get('sizes',[]) or
                        folder not in {f'{context}/{size}' for context in ('apps','categories') for size in package.get('sizes',[])}):
                    errors.append('Theme directory is missing or invalid: '+folder)
        except (KeyError,configparser.Error):errors.append('Invalid index.theme')
        if not draft and package['selection']!='cleared-only':
            errors.append('Theme package still contains the development selection')
    elif not draft:
        errors.append('Selectable theme package is missing')
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        if path.is_symlink():
            errors.append(f"Symlink not allowed: {relative}")
        elif path.is_file():
            if path.suffix in {".desktop", ".dockitem", ".log"} or relative.parts[0] in {"private", "backups", "sources", "artifacts"}:
                errors.append(f"Private file type: {relative}")
            if PRIVATE.search(path.read_bytes().decode("utf-8", errors="replace")):
                errors.append(f"Machine-specific path found: {relative}")

    if not draft:
        if catalog.get("release_status") != "ready":
            errors.append("Release status is still draft")
        if "- [ ]" in (ROOT / "RELEASE_CHECKLIST.md").read_text():
            errors.append("Release checklist has unfinished items")
    print(f"Checked {len(assets)} SVG assets and {len(bundle_expected)} companion files ({'draft' if draft else 'release'} mode).")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Privacy and integrity checks passed." if draft else "Release checks passed.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", action="store_true", help="Check integrity/privacy without claiming release readiness")
    args = parser.parse_args()
    raise SystemExit(check(args.draft))

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Verify source pixels and GTK/Qt lookup without touching a desktop session.

Development dependencies: Pillow, PyGObject/GdkPixbuf/librsvg, Gtk 3 and PyQt6.
The published installer and integrity checker do not require these libraries.
"""
import json
import os
from pathlib import Path

# Always use an isolated offscreen Qt backend, not the user's platform theme.
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QPA_PLATFORMTHEME'] = 'generic'
os.environ['QT_STYLE_OVERRIDE'] = 'fusion'
os.environ['QT_SCALE_FACTOR'] = '1'
os.environ['QT_FONT_DPI'] = '96'

import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
from PIL import Image
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon, QImage
from PyQt6.QtWidgets import QApplication
from make_previews import render

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = json.loads((ROOT/'assets.json').read_text())
    package = json.loads((ROOT/'theme-files.json').read_text())
    by_key = {a['key']:a for a in catalog['assets']}
    entries = [e for e in package['files'] if e.get('format')=='png']
    references = {}
    for entry in entries:
        key,size = entry['asset_key'],entry['size']
        if (key,size) not in references:
            references[key,size] = render(ROOT/by_key[key]['file'],size).tobytes()
        with Image.open(ROOT/entry['file']) as image:
            if image.convert('RGBA').tobytes()!=references[key,size]:
                raise AssertionError('PNG differs from editable artwork: '+entry['file'])
    print(f'Source rendering: {len(entries)} PNG aliases match {len(references)} source/size renders.')
    app = QApplication([])
    QIcon.setThemeSearchPaths([str(ROOT/'theme')])
    QIcon.setThemeName(package['name'])
    QIcon.setFallbackThemeName('')
    gtk = Gtk.IconTheme.new()
    gtk.set_search_path([str(ROOT/'theme')])
    gtk.set_custom_theme(package['name'])
    qt_count,gtk_count = 0,0
    # Five exact common dock/toolbox sizes cover every name and both contexts.
    for entry in entries:
        size=entry['size']
        if size not in (24,40,48,64,128):
            continue
        path = ROOT/entry['file']
        name = path.stem
        icon = QIcon.fromTheme(name)
        if icon.isNull():
            raise AssertionError('Qt cannot find icon: '+name)
        image = icon.pixmap(QSize(size,size)).toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        bits=image.bits(); bits.setsize(image.sizeInBytes())
        if image.width()!=size or image.height()!=size or bytes(bits)!=references[entry['asset_key'],size]:
            raise AssertionError(f'Qt displays wrong artwork: {name} at {size}')
        qt_count+=1
        info=gtk.lookup_icon(name,size,Gtk.IconLookupFlags.FORCE_SIZE)
        if info is None or Path(info.get_filename()).resolve()!=path.resolve():
            # A duplicate name across contexts is allowed only for the same pixels.
            if info is None or Image.open(info.get_filename()).convert('RGBA').tobytes()!=references[entry['asset_key'],size]:
                raise AssertionError(f'GTK resolves wrong artwork: {name} at {size}')
        gtk_count+=1
    print(f'Qt pixel comparisons: {qt_count}; GTK exact-size lookups: {gtk_count}; all passed.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())

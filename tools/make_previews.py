#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Build clean artwork-only contact sheets; no screenshots or user configuration."""
import hashlib
import json
from pathlib import Path
import textwrap

import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def render(path, size):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, size, False)
    mode = 'RGBA' if pixbuf.get_has_alpha() else 'RGB'
    return Image.frombytes(mode, (pixbuf.get_width(), pixbuf.get_height()), pixbuf.get_pixels(),
                           'raw', mode, pixbuf.get_rowstride()).convert('RGBA')


def font(size):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)


def sheet(assets, title, filename, cols=4):
    width, cell, top = cols * 240, 190, 94
    rows = (len(assets) + cols - 1) // cols
    result = Image.new('RGB', (width, top + rows * cell + 32), '#16181c')
    draw = ImageDraw.Draw(result)
    draw.text((28, 20), title, font=font(27), fill='white')
    draw.text((28, 58), 'Monochrome Icons · v0.1.0 · distributed artwork', font=font(17), fill='#aeb6c2')
    for index, asset in enumerate(assets):
        x, y = (index % cols) * 240, top + (index // cols) * cell
        icon = render(ROOT / asset['file'], 104)
        result.paste(icon, (x + (240 - icon.width) // 2, y + 8), icon)
        lines = textwrap.wrap(asset['name'], width=23, max_lines=2, placeholder='…')
        for number, line in enumerate(lines):
            draw.text((x + 120, y + 117 + number * 21), line, font=font(17), fill='white', anchor='mt')
        short = textwrap.shorten(asset['key'], width=30, placeholder='…')
        draw.text((x + 120, y + 166), short, font=font(12), fill='#939da9', anchor='mt')
    path = ROOT / 'previews' / filename
    path.parent.mkdir(exist_ok=True)
    result.save(path, optimize=True)
    return {'file': 'previews/' + filename, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    catalog = json.loads((ROOT / 'assets.json').read_text())
    assets = catalog['assets']
    if any(a['review_status'] != 'cleared' for a in assets):
        raise ValueError('Do not render pending artwork into public previews')
    menu = [a for a in assets if a['key'].startswith(('menu-', 'xfsm-'))]
    weather = [a for a in assets if 'weather_assignment' in a]
    apps = [a for a in assets if a not in menu and a not in weather]
    previews = []
    for start in range(0, len(apps), 32):
        page = start // 32 + 1
        previews.append(sheet(apps[start:start+32], f'Applications · {page}', f'applications-{page:02}.png'))
    previews.append(sheet(menu, 'Menus and session actions', 'menu-session.png'))
    previews.append(sheet(weather, 'Weather · day, night and precipitation', 'weather.png'))
    catalog['previews'] = previews
    (ROOT / 'assets.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n')
    print(f'Generated {len(previews)} clean sheets from {len(assets)} reviewed entries.')


if __name__ == '__main__':
    main()

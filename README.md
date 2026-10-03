# Monochrome Icons

White drawings on black faces, with a consistent rounded-square outline. Made for a dark Xfce desktop and Plank, while keeping applications recognizable.

![Application sample](previews/applications-01.png)

## v0.1.1

206 reviewed SVG catalog entries: 146 application/dock entries, 16 menu/panel entries, 6 session actions and 38 weather conditions. Counts include purposeful aliases, not 206 unique drawings. The ready-to-install theme contains 4,120 PNGs at ten sizes (16/22/24/32/40/48/64/96/128/256), plus its index. The optional Xfce Weather companion remains 114 PNGs at 22, 48 and 128 pixels.

This release adds **125 portable native icon-name mappings**, including MX Tools and the newly source-verified MX Viewer. These names let a running app keep its monochrome icon when Plank resolves its system launcher, and let MX Toolbox find supported icons without modifying system launchers. Runtime PNGs avoid Qt's incomplete rendering of the nested SVG artwork; editable SVG sources remain included. Generic terminal requests use a terminal drawing, not the aerc mail mark.

This is a **WhiteSur-compatible icon-theme overlay**, not a GTK or window-manager theme. It inherits `WhiteSur-dark,hicolor`; icons outside its coverage fall back to those themes. Install WhiteSur-dark separately for the intended fallback appearance. The existing pink/dark GTK styling is independent and is not changed by this package.

Some assets could not yet be verified for redistribution: [35 entries are omitted](OMITTED.md), including Brave Origin and several MX utilities. The regular WhiteSur-derived Brave Browser icon is included. Omitted artwork is not in the repository or previews; nothing has been removed from the original desktop installation. This release does not claim monochrome coverage for every MX Toolbox card.

## Previews

The pictures show only the distributed artwork, not private desktop screenshots.

- [Applications 1](previews/applications-01.png) · [2](previews/applications-02.png) · [3](previews/applications-03.png) · [4](previews/applications-04.png) · [5](previews/applications-05.png)
- [Menu and session icons](previews/menu-session.png)
- [Weather conditions](previews/weather.png)

## Install

Requires Python 3.9+ on Linux. Xfce activation also requires `xfconf-query` and an active Xfce session. Installing the prebuilt package needs no imaging or Qt libraries. Rebuilding icons or previews has separate dependencies below. No administrator privileges are needed.

Download and extract the release, or clone this repository:

```sh
git clone https://github.com/antoinebaudrimont-beep/monochrome-icons.git
cd monochrome-icons
python3 tools/check_release.py
python3 tools/install_theme.py install --dry-run
python3 tools/install_theme.py install
```

Then choose **Monochrome Icons** in **Xfce Settings → Appearance → Icons**. Alternatively use `install --activate` instead of the final command to select it automatically. Installing without `--activate` changes no session settings.

The checked-in `theme/MonochromeIcons` is ready to install. The indexed runtime directories contain only PNGs, so Qt cannot choose an unsupported nested SVG instead. Rebuild from editable `icons/*.svg` after installing the rendering dependencies listed below:

```sh
python3 tools/build_theme.py --cleared-only
```

### Application and menu overrides

Native icon names listed in `assets.json` work simply by selecting this theme. Some launchers use shared or absolute icon paths. Selecting a theme cannot override an absolute `Icon=` path, and apps sharing one native name share one drawing (for example MX Welcome/About MX Linux). Per-user launcher mapping can give a menu or pinned shortcut its distinct icon, but does not guarantee that a running window or an application reading system launchers will use that override. To map supported installed applications and menu categories, opt in on the initial install:

```sh
python3 tools/install_theme.py install --known-apps --menu --activate --dry-run
python3 tools/install_theme.py install --known-apps --menu --activate
```

The installer copies matching launchers/categories into per-user XDG directories and modifies only their main `Icon` fields. `Exec`, URL arguments, default-browser associations, desktop actions and Plank layout are preserved. Missing applications are skipped. Existing overrides are backed up. It never restarts Plank or the panel.

Profile-specific web apps and dynamic calendar launchers are deliberately excluded from automatic mapping. To map one of your own launchers explicitly, add e.g. `--map my-browser.desktop=chawan` on the initial install. The application must already be installed; this package does not create launcher commands. Available keys and supported portable desktop IDs are in [assets.json](assets.json).

The Applications grid has the `gnome-applications` and `applications-other` aliases. For a custom Whisker menu button, choose the `monochrome-menu-mx-menu-button` icon in its preferences; button settings are not changed automatically. Dock launchers with hardcoded icon paths likewise need an explicit mapping or a manual icon selection.

**Calendar examples remain static in v0.1.1.** No calendar timer/helper or existing daily-updating icon is changed. Portable dynamic-calendar integration is deferred; do not point a date-writing helper at managed theme files, because restore detects subsequent edits.

### Xfce Weather companion

The Weather plugin uses a separate icon directory, not the desktop icon theme. On the initial install, add `--weather`:

```sh
python3 tools/install_theme.py install --weather --dry-run
python3 tools/install_theme.py install --weather
```

Then choose **Monochrome Weather** in **Weather Preferences → Appearance**. Forecast location, units and other settings are not changed. If a `monochrome` Weather directory already exists, the installer refuses to overwrite it. The companion is optional.

All options can be combined on a single initial install. The installer refuses to replace an existing `MonochromeIcons` directory; restore a prior managed installation before reinstalling/updating. If there is a manually installed theme with that name, move it aside yourself first after keeping a backup.

### Upgrade from v0.1.0

Download/extract v0.1.1 into a separate directory. Use your v0.1.0 backup manifest to restore the prior managed install (see below), then install v0.1.1 with your desired options. If you installed Weather too, select your previous Weather icon set before restore and select Monochrome Weather again after reinstall. The installer deliberately does not merge or overwrite an existing theme. The older GitHub release remains available. Updating the repository or downloading a release alone changes no desktop settings.

## Restore

Installation prints the path to its private backup `manifest.json`. Keep that path. Run:

```sh
python3 tools/install_theme.py restore /absolute/path/to/manifest.json --dry-run
python3 tools/install_theme.py restore /absolute/path/to/manifest.json
```

If you selected a Weather companion manually, first select your previous Weather icon set. If you selected the desktop icon theme manually, first choose your previous desktop icon theme. An activation performed with `--activate` is restored automatically.

Restore checks **every managed file before changing anything**. If an icon/launcher has been edited, a backup is missing, or an automatically activated theme has since changed, restore stops for review. Existing launchers are restored byte-for-byte with their prior permissions; only unchanged files created by the installer are deleted. Extra user files and backups are retained. There is no force-delete option. An interrupted install may require reviewing its retained manifest rather than forcing a restore.

## Validation and development

```sh
python3 tools/check_release.py
python3 tools/test_build.py
python3 tools/test_install.py
```

Tests use temporary homes and do not activate or write to your desktop. The checker verifies catalog/package checksums, PNG sizes and source references, native-name assignments, safe SVG content, all Weather sizes, review gates and absence of private machine paths/launcher files. It is an integrity gate, not a guarantee that every future asset is licensed correctly.

To rebuild the runtime theme or clean preview sheets, install Python Pillow and PyGObject with the GdkPixbuf/librsvg SVG loader (on Debian: `python3-pil python3-gi gir1.2-gdkpixbuf-2.0 librsvg2-common`), then run:

```sh
python3 tools/build_theme.py --cleared-only
python3 tools/make_previews.py
python3 tools/check_release.py
```

The builder validates all previous managed output before replacing it; edited or unlisted files stop the build. It retires only unchanged files listed in the previous build manifest, not user data.

For source-pixel verification and GTK/Qt lookup regression tests, also install Gtk 3 introspection and PyQt6 (`gir1.2-gtk-3.0 python3-pyqt6` on Debian), then run `python3 tools/test_rendering.py`. Qt runs offscreen; no applications or system tools are launched. Every PNG is compared with its editable SVG source; every runtime name is checked through GTK and pixel-compared through Qt at five common dock/toolbox sizes.

## License and credits

Original project artwork, frames and code: **GPL-3.0-only**. Upstream attribution and license notices remain applicable. In particular, Robin Jarry's original **aerc mark is CC BY 4.0**, not relicensed as our own artwork. WhiteSur, Foliate and MX credits and source evidence are documented in [ATTRIBUTION.md](ATTRIBUTION.md), [per-asset credits](notices/ASSET-CREDITS.md) and [assets.json](assets.json). Full license texts are included.

Application names and marks identify their respective applications. Copyright licensing does not grant trademark rights or imply endorsement. This project is not affiliated with the applications it depicts.

Further coverage and portable integrations: [ROADMAP.md](ROADMAP.md).

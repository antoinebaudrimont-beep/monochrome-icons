# ArtCraft integration

The seven original functional drawings extend the existing Monochrome Icons frame and palette. They do not reproduce ArtCraft's trademark artwork. Licensing and credits are in `ATTRIBUTION.md` and `assets.json`.

## Verified Linux identities

These fields were checked against the installed Debian packages supplied by ArtCraft Launcher on 2026-11-04. The desktop IDs are the icon names below plus `.desktop`. `StartupWMClass` matches each icon name and was verified against a live X11 window for all six document apps.

| Application | Package version | Native icon name | Main Exec |
| --- | --- | --- | --- |
| ArtCraft Launcher | 0.14.0-1 | ai.storyteller.artcraft-launcher | artcraft-launcher |
| PhotoCraft | 0.20.1-1 | ai.storyteller.photocraft | photocraft %F |
| VectorCraft | 0.21.0-1 | ai.storyteller.vectorcraft | vectorcraft %F |
| WordCraft | 0.15.1-1 | ai.storyteller.wordcraft | wordcraft %F |
| GridCraft | 0.16.0-1 | ai.storyteller.gridcraft | gridcraft %F |
| DeckCraft | 0.15.0-1 | ai.storyteller.deckcraft | deckcraft %F |
| PdfCraft | 0.18.1-1 | ai.storyteller.pdfcraft | pdfcraft %U |

The packages install icons into the standard `hicolor` theme, including scalable SVG and PNG files at 16, 24, 32, 48, 64, 128, 256 and 512 pixels. This theme supplies native-name overrides and `monochrome-<asset-key>` aliases. The installer preserves the actual launcher's commands, actions, MIME declarations and window class.

## Keep an existing desktop's appearance

The optional ArtCraft-only overlay contains 210 PNGs and one index. Its `ArtCraftMonochrome` theme inherits the currently selected theme, so existing artwork, dynamic calendars and menu/category icons remain with that theme. It installs all three names for each drawing at ten sizes. This mode cannot install Weather or menu-category artwork.

For local testing of this unreleased branch:

```sh
python3 tools/install_theme.py install --allow-draft --artcraft-overlay --known-apps --activate --dry-run
python3 tools/install_theme.py install --allow-draft --artcraft-overlay --known-apps --activate
```

The existing-theme name may be supplied with `--base-theme THEME`; activation refuses a base different from the current theme. Isolated tests using `--home` require an explicit base. Existing overlay directories are never overwritten. Keep the printed restore manifest and follow the normal conflict-aware restore procedure in `README.md`.

The overlay only changes theme selection and the seven matching launcher icon fields. It does not install/uninstall apps, change MIME defaults or Plank layout, or modify system launchers. Migration of those settings is separate and must use actual installed launchers, backups and dependency dry-runs.

## Desktop and tray limits

Absolute `Icon=` paths bypass theme lookup; use the backed-up per-user launcher mappings to replace those fields. A Plank pin may itself refer to an absolute launcher URI; replacing an app requires updating that URI to the replacement's real desktop file while preserving the dock order. Native icon aliases cover consumers that resolve system launchers for running windows. Verify matching on the target desktop; metadata and toolkit lookup checks are not a visual inspection of the dock.

ArtCraft Launcher 0.14.0's live StatusNotifierItem reports empty `IconName` and `IconThemePath` properties and a 64×64 embedded `IconPixmap`. A desktop icon-theme override cannot safely replace that bitmap. No binary patch or vendor artwork modification is included.

## Compatibility checks and boundaries

Local tests passed opening and saving/exporting then reopening disposable copies in ten formats: PSD, XCF, SVG, AI, DOCX, DOC, XLSX, CSV, PPTX and PDF. The XLSX calculation and round-trip checker also passed. This is sample-level verification, not a guarantee of fidelity for every document or feature.

- WordCraft imports legacy `.doc`; the tested save target was `.docx`.
- PhotoCraft reads the tested XCF file and exports a reopened PSD. It warns about linear-light versus gamma-encoded blending differences. Its installed desktop entry does not advertise XCF; any local association added after testing is a separate, backed-up change.
- DeckCraft's installed MIME list advertises PPTX-family files and its own document format, not OpenDocument presentations. Do not assign `.odp` to it without evidence of support.
- Existing browser, text-editor, scientific-file and general image-viewer defaults should remain independent of a suite migration.

Keep document tests and screenshots containing private files outside this repository. Do not merge this branch until the user has reviewed and explicitly approved it.

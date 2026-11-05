# Changelog

## v0.2.0 — 2026-11-05

- Add original monochrome icons for ArtCraft Launcher, PhotoCraft, VectorCraft, WordCraft, GridCraft, DeckCraft and PdfCraft.
- Add the seven published `ai.storyteller.*` Linux icon names and desktop IDs while preserving application commands and MIME declarations.
- Expand the reviewed catalog to 213 entries and the PNG runtime theme to 4,330 files at ten sizes.
- Add an isolated installer regression test for all seven ArtCraft launcher mappings.
- Add an ArtCraft-only overlay mode that inherits the active theme and preserves unrelated artwork, with isolated conflict/restore tests.
- Verify actual package identities, six live X11 window classes, ten document import/round-trip samples and live GTK icon resolution; document the embedded tray bitmap limitation.
- Add an optional runtime tray adapter that preserves the original ArtCraft A silhouette in white, forwards clicks/menus and restores the original item when stopped. No vendor artwork is distributed or patched; alpha preservation and bounded bitmap handling have isolated tests.
- Document refreshing Plank after obsolete package removal; the user confirmed both dock and tray appearance/functionality on the target desktop.

Installed launchers, running-window matching, representative documents and rollback were verified on the target MX Linux desktop. The user confirmed dock/tray appearance and menu behavior and approved merge and versioned publication on 2026-11-05.

## v0.1.1 — 2026-10-03

- Add 125 portable native icon-name mappings for running-app recognition in Plank and supported system-launcher readers such as MX Toolbox.
- Replace indexed runtime SVGs with 4,120 PNGs at ten sizes, avoiding Qt's incomplete nested-SVG rendering. Editable SVG sources remain distributed.
- Add MX Viewer after verifying every source pixel against pinned upstream artwork and its artwork-applicable GPL-3+ notice. The reviewed catalog now has 206 entries; 35 remain omitted.
- Keep generic terminal and settings names generic; shared native names use one canonical drawing.
- Add builder safety tests, native-alias integrity checks and offscreen GTK/Qt/source-pixel regression tests; refresh clean preview sheets.
- Document conservative v0.1.0 upgrade/restore and remaining shared-name, absolute-path and coverage limitations.

Weather artwork is unchanged. No system launcher files, app commands, browser associations, Plank layout, GTK styling or dynamic-calendar helpers are changed by publishing or downloading this release.

## v0.1.0 — 2026-10-02

First public, icon-only release:

- 205 reviewed SVG catalog entries: 145 application/dock, 16 menu/panel, 6 session and 38 Weather conditions.
- Installable `MonochromeIcons` overlay inheriting `WhiteSur-dark,hicolor`.
- Optional Xfce Weather companion: 114 PNGs at 22/48/128 pixels.
- Clean phone-friendly preview sheets, editable artwork and per-asset source/license evidence.
- Per-user installer with dry-run, opt-in portable app/menu mapping, backups and conservative restore.
- Original project artwork/code under GPL-3.0-only; upstream notices and aerc's CC BY 4.0 retained.
- 36 uncleared catalog entries omitted from all distributed artwork and previews.

This release does not change GTK/Xfwm styling, app commands, browser defaults, Plank layout or existing dynamic calendars. Calendar examples are static; Weather activation is manual. See README for coverage, installation and restoration limits.

# NAnners Creator Hub — 0.1.0-dev7 visual warnings

## Warning visibility improvement

The Kdenlive marker export dialog now displays:

- A high-contrast **amber frame-rate mismatch banner** with a border and bold text when the selected FPS differs from Kdenlive's saved preference
- A high-contrast **red export-blocking banner** when section data cannot produce valid markers
- Both banners adapt to KDE's light/dark color palette
- The mismatch banner disappears automatically when the frame-rate selections agree
- The original confirmation prompt remains before exporting a mismatched selection

A saved Kdenlive preference may not match the currently open Kdenlive project's real FPS. Always verify the project settings.

## User test

1. Open NAnners Creator Hub from the KDE application menu.
2. Open your saved `tutorial.json` project.
3. Click **Kdenlive Markers** and check that 60 FPS is initially selected on your CachyOS system.
4. Change the frame rate to 30 FPS. Confirm the prominent amber banner appears.
5. Change it back to 60 FPS. Confirm the banner disappears.
6. With a section missing valid media or ranges in a disposable test project, confirm the red export-blocking banner appears and export is disabled.

No videos, audio files, Kdenlive projects or existing user project JSON files are modified by this update.

## License

MIT — see `LICENSE`.

## Release status

This is development checkpoint `0.1.0-dev7`, not final `v0.1.0`.

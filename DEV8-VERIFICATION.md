# NAnners Creator Hub — 0.1.0-dev8 UI checkpoint

## Kdenlive Timeline Marker Export dialog

The dialog now starts at **640 × 500 pixels**, with a minimum height of **500 pixels**.

The Kdenlive FPS helper label is now a **full-width row** below the frame-rate selector. This keeps the saved-preference message from being squeezed beside the selector when the warning banner appears.

The high-contrast amber frame-rate warning and red export-blocking warning from dev7 remain unchanged. The software still prompts for confirmation when FPS differs from Kdenlive's saved preference.

## Desktop check

1. Open NAnners Creator Hub from the KDE app menu (dev8).
2. Open `tutorial.json`, then **Kdenlive Markers**.
3. Confirm the slightly taller window and legible full-width FPS helper.
4. Change 60 FPS to 50 or 30 FPS to show the amber banner.
5. Confirm helper text is not cut off and the warning remains visible.
6. Return to 60 FPS and confirm warning disappears.

This update changes only interface layout. Source recordings, `.kdenlive` projects, project JSON files and existing reports remain untouched.

MIT license remains in `LICENSE`; final `v0.1.0` tagging is still pending.

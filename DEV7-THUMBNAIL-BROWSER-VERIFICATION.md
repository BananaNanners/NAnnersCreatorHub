# NAnners Creator Hub 0.2.0-dev7 — Thumbnail Browser & Visual Footage Discovery

## New features

- **Browse Thumbnails…** button above the media table in Assisted Editing.
- Select any imported video recording; the browser samples 12 evenly spaced frames with FFmpeg, displaying thumbnails and timestamp labels.
- Extraction runs one bounded asynchronous FFmpeg process at a time. The UI remains responsive, and closing or switching recordings stops the current job.
- Select or double-click a thumbnail to open the existing video preview **at that source timestamp**.
- For footage already assigned to the selected tutorial section, the preview retains its explicit **Apply Range to Section** action.
- For an imported video not assigned to the selected section, the preview is **read-only**. Assign that video through the Footage selector before applying in/out points.
- All preview, scanning, and thumbnail operations are read-only. No thumbnail files are saved to the footage folder, and original video, WAV, project JSON, and Kdenlive files are untouched.

## Verification

- 106 automated regression tests using the Qt-safe runner.
- Real FFmpeg extraction from the user's imported MKV succeeded at 0.500, 26.216, and 51.933 seconds; three valid JPEG frames were produced and the source video SHA-256 remained unchanged.
- Headless tests cover valid/invalid sampling, bounded FFmpeg arguments, browser no-file-creation and cancellation, and preview jumping to a selected timestamp.
- KDE desktop playback, display and thumbnail selection still need the user's hands-on verification.

## KDE desktop test

1. Open NAnners Creator Hub and verify window title **0.2.0-dev7**.
2. Load the tutorial project and choose **Browse Thumbnails…** above the media table.
3. Verify that the imported video appears in Recording and 12 thumbnails with timestamps load.
4. Select a thumbnail around the middle of the recording, click **Preview Selected Moment** and verify the video preview opens near that timestamp.
5. Play and scrub to confirm preview controls still work.
6. Close the preview without Apply: original section ranges should remain unchanged and project state should stay SAVED.
7. When using an imported video not assigned to the section, confirm **Apply Range to Section** is disabled.
8. With an already assigned video, set a valid IN/OUT range and explicitly Apply; the section becomes **UNSAVED CHANGES**.
9. Save only if you want to keep those changes. Existing recording and audio files remain unchanged.

## Rollback

Previous versions including 0.2.0-dev6 and stable 0.1.0 remain installed. Run:
```
cd ~/Projects/NAnnersCreatorHub
python tools/manage_install.py list
python tools/manage_install.py rollback 0.2.0-dev6
```

This development checkpoint is local only. No GitHub release is modified.

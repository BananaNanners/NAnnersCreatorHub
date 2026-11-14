# NAnners Creator Hub — 0.2.0-dev5 footage preview

## New feature

A **Preview / Set Range…** button appears beside the assigned footage in each tutorial section. It opens a separate Qt Multimedia video preview dialog with:

- Video display and audio through the existing Qt Multimedia backend
- Play/Pause and Stop buttons
- Scrubbable position slider and elapsed/total time
- IN and OUT spin boxes in seconds (millisecond precision)
- **Mark IN at Playhead** and **Mark OUT at Playhead**
- **Apply Range to Section** (only this action updates the project)
- **Cancel / Close**, which does not change the project

The selected video must be an existing assigned video reference. The dialog checks that IN is before OUT and, when known, that the selected range does not exceed the source media duration. The original recording is never cut, altered, or overwritten. A successful Apply updates the section source in/out points in memory and marks the project **UNSAVED** until Save Project is clicked.

## Verification

- Automated tests cover invalid ranges, dialog cancellation, range application, source-file preservation, and unsaved-state behavior.
- Linux Qt Multimedia video widget and FFmpeg backend are installed and were verified.
- Preview works in a separate window to avoid crowding the Assisted Editing form.
- No automatic Kdenlive timeline editing is part of this checkpoint.

## Desktop test

1. Open the KDE launcher. Window title should show **0.2.0-dev5**.
2. Open your saved tutorial. Select a section with an assigned video and click **Preview / Set Range…**.
3. Confirm video plays (with audio, if present), Play/Pause works, and slider can scrub.
4. Click **Mark IN at Playhead**, move forward, then **Mark OUT at Playhead**.
5. Click **Cancel / Close** and confirm the original section in/out points are unchanged.
6. Reopen the preview, choose a valid range, click **Apply Range to Section**.
7. Confirm new section in/out points are visible; project status says **UNSAVED CHANGES**.
8. Save the project only if you're happy with the selected range. The video file itself remains untouched.

## Rollback

The previous stable release and all dev4 versions are retained. Use `python tools/manage_install.py list` and `rollback 0.2.0-dev4-fix2` from the repository if needed. This dev5 checkpoint is local only; no GitHub push was performed.

# NAnners Creator Hub — 0.2.0-dev6 waveform and narration synchronization

## Included

- **Sync / Waveform…** button beside the section's narration selector in Assisted Editing.
- Separate **Narration Sync** dialog with read-only narration waveform extracted through FFmpeg, narration playback, and scrubbing.
- A comparison between narration length and the selected footage segment. Both are displayed from the proposed section timeline start, not the video's absolute source IN.
- Editable footage source IN/OUT controls and **Match Footage Length to Narration**: sets a proposed source OUT from existing IN + narration duration, if the source is long enough.
- **Apply Range to Section** is the only action that changes the in-memory section. Cancel leaves every setting unchanged.
- The project shows **UNSAVED CHANGES** after Apply; **Save Project** is still required to persist the changed source range.
- Audio and video files are only read and never cut or overwritten.
- Waveform rendering is limited to clips <= 15 minutes for bounded processing; duration comparison and audio playback remain available on longer files.
- The waveform is a visual timing guide, not an edited Kdenlive timeline or a waveform overlay of the video track.

## Automated checks

- 98 standard regression tests and 8 isolated sync rehearsal tests (5 overlap; 101 unique checks) covering waveform peak calculation, duration differences, invalid bounds, narration-length matching, cancellation and explicit Apply. Three consecutive runs of the Qt-safe test runner (`python tools/run_tests.py`) exited cleanly.
- Isolated real FFmpeg waveform extraction generated 420 peak bins and preserved the input WAV byte-for-byte.
- The isolated GUI rehearsal runs through `QT_QPA_PLATFORM=offscreen PYTHONPATH=src python tests/sync_gui_rehearsal.py`. GUI unit tests mock audio loading and asynchronous process start; real waveform decoding is tested separately through FFmpeg. Use `python tools/run_tests.py` for full offscreen regression: the direct unittest discovery command can intermittently crash during PySide widget teardown after passing its assertions. The new runner explicitly destroys test widgets while QApplication is still alive.
- Final playback and visible waveform must be validated interactively on the CachyOS KDE desktop.

## Desktop verification

1. Open NAnners Creator Hub. Confirm the title shows **0.2.0-dev6**.
2. Load your tutorial project and select a section with narration and assigned footage.
3. Click **Sync / Waveform…** next to Narration; confirm the waveform appears.
4. Play and scrub the narration audio, confirming sound.
5. Check that the displayed narration length, selected footage length, and longer/shorter difference make sense.
6. Click **Match Footage Length to Narration**. The proposed OUT should change to IN + narration duration (if enough source footage remains).
7. Click **Cancel / Close**. The original section IN/OUT points and saved/unsaved state should remain unchanged.
8. Reopen the dialog, select a valid range, click **Apply Range to Section**. The range should update and the project should display **UNSAVED CHANGES**.
9. Save only if satisfied. Existing WAVs, footage, and Kdenlive projects must remain untouched.

## Rollback

The stable v0.1.0 and previous dev releases, including 0.2.0-dev5, remain installed. Development changes are local and have not been published to GitHub.

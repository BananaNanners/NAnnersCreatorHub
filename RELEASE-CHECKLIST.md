# NAnners Creator Hub — 0.1.0-dev6 verification

## Kdenlive marker timing

Kdenlive marker JSON positions are **frame indices**. A marker at frame 240 is at
8 seconds in a 30 FPS timeline, or 4 seconds in a 60 FPS timeline.

The Kdenlive Markers dialog now reads the saved `project_fps` preference in
`~/.config/kdenliverc` where available and uses it as the initial export
selection. It warns when the user selects a different frame rate.

**Important:** This preference might differ from the frame rate of the
currently open Kdenlive project. Always verify the actual FPS from that
project's Project Settings before exporting. No Kdenlive config is modified.

## License

MIT — see `LICENSE`. Copyright (c) 2026 NAnners Creator Hub contributors.

## Installed versions

The installer retains previous releases under the user's XDG data directory.
It does not modify user recordings, tutorial manifests, or existing Kdenlive
projects.

## Verification

- Automated tests: full regression including preference detection
- GUI preview: saved preference defaults to 60 FPS; mismatch warning appears
- Real Kdenlive multi-marker timing: pending a new 60 FPS import test

Once the user verifies that frame 480 is displayed at 00:00:08:00 in their
60 FPS test project, we can mark multi-marker integration validated.

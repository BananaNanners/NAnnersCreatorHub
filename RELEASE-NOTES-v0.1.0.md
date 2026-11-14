# NAnners Creator Hub v0.1.0 — Initial release

## Overview

First local-first assisted YouTube tutorial production workflow for CachyOS/Linux using PySide6 and FFprobe, complementing OBS, Kokoro and Kdenlive.

## Included

- Section-by-section script, narration and video reference organization
- Source-range selection, review statuses and non-blocking timing warnings
- Read-only media inspection, missing file detection, and project JSON persistence
- Markdown readiness checklist export
- Kdenlive timeline guide JSON export with selectable rational FPS and marker preview
- Kdenlive saved-FPS preference detection, high-contrast warning banners and blocking invalid-export messages
- Polished marker dialog (640 × 500; full-width FPS hint)
- User-local installation and KDE application launcher with version retention and rollback
- MIT license

## Validation

- All dev1–dev8 milestones were desktop tested on CachyOS/KDE.
- Existing project save/reopen, media import and external playback passed.
- Readiness report export and marker guide import passed in Kdenlive 26.08.3.
- Two-marker position was verified at 00:00:08:00 in a 60 FPS Kdenlive project.
- Automated test suite and installer rollback rehearsals cover version retention and original file preservation.
- Final v0.1.0 installation and launch must also be checked after installation.

## Known limitations

- Assisted Editing Mode only; Automatic Timeline Mode planned for later
- Filename-based footage suggestions require human confirmation
- Exported marker positions assume sequential, gapless planning ranges, not the user's actual edited timeline
- FPS preference is not guaranteed to match an open Kdenlive project's FPS
- No embedded video editor, visual content matching, or automatic transition creation
- Installer relies on existing system Python/PySide6/FFprobe and has not been packaged as an Arch/CachyOS system package
- Projects are non-destructive, but save operations replace the chosen project JSON atomically; make external backups for important projects

## Source and license

MIT, see LICENSE. Git tag: v0.1.0.

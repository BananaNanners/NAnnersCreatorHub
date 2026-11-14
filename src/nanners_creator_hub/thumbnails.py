"""Read-only video thumbnail sampling plans and FFmpeg command arguments.

No user recordings or project manifests are ever written by this module.
"""
from __future__ import annotations

import math
from pathlib import Path

MAX_THUMBNAILS = 12


def video_entries(media: list[dict]) -> list[dict]:
    return [
        entry for entry in media
        if entry.get("kind") in ("Video", "Video + Audio")
        and isinstance(entry.get("path"), str) and entry["path"]
    ]


def thumbnail_times(duration: float, count: int = MAX_THUMBNAILS) -> tuple[float, ...]:
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Video duration must be positive and finite.")
    if not 1 <= count <= MAX_THUMBNAILS:
        raise ValueError("Choose between 1 and 12 thumbnail frames.")
    # Keep the last sample away from EOF, where decoding can fail.
    if count == 1:
        return (round(min(0.5, duration / 2), 3),)
    margin = min(0.5, duration / 4)
    start = margin
    end = max(start, duration - margin)
    return tuple(round(start + (end - start) * i / (count - 1), 3) for i in range(count))


def thumbnail_args(path: Path, at_seconds: float) -> list[str]:
    if not math.isfinite(at_seconds) or at_seconds < 0:
        raise ValueError("Thumbnail timestamp must be nonnegative and finite.")
    return [
        "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", f"{at_seconds:.3f}", "-i", str(path),
        "-map", "0:v:0", "-frames:v", "1",
        "-vf", "scale=320:180:force_original_aspect_ratio=decrease",
        "-an", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
    ]


def timestamp_label(seconds: float) -> str:
    total = max(0, round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}" if hours else f"{minutes:02}:{secs:02}"

"""Read-only media inspection through FFprobe.

No function in this module writes to the inspected file.
"""
from __future__ import annotations

import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any


class MediaProbeError(RuntimeError):
    """A file could not be inspected as supported media."""


def _duration(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return round(result, 3) if math.isfinite(result) and result >= 0 else None


def _fps(stream: dict) -> float | None:
    for field in ("avg_frame_rate", "r_frame_rate"):
        try:
            rate = Fraction(stream.get(field, "0/0"))
            if rate > 0:
                return round(float(rate), 3)
        except (ValueError, TypeError, ZeroDivisionError):
            continue
    return None


def inspect_media(source: str | Path, timeout: int = 20) -> dict:
    """Return serializable metadata for a regular file; never mutate source."""
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise MediaProbeError("File is missing or is not a regular file")
    try:
        completed = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_format", "-show_streams",
                "-of", "json", "-i", str(path),
            ],
            capture_output=True, text=True, errors="replace", timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise MediaProbeError("FFprobe is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaProbeError(f"FFprobe timed out after {timeout} seconds") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        message = detail[-1] if detail else "FFprobe failed"
        raise MediaProbeError(message[:350])
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MediaProbeError("FFprobe returned invalid JSON") from exc
    streams = document.get("streams", [])
    if not isinstance(streams, list):
        raise MediaProbeError("FFprobe did not return valid streams")
    videos = [
        s for s in streams if s.get("codec_type") == "video"
        and not s.get("disposition", {}).get("attached_pic", 0)
    ]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos and not audios:
        raise MediaProbeError("No usable audio or video streams found")
    video = videos[0] if videos else {}
    audio = audios[0] if audios else {}
    fmt = document.get("format") or {}
    duration = _duration(fmt.get("duration"))
    if duration is None:
        options = [_duration(s.get("duration")) for s in videos + audios]
        known = [v for v in options if v is not None]
        duration = max(known) if known else None
    stat = path.stat()
    kind = "Video + Audio" if videos and audios else ("Video" if videos else "Audio")
    return {
        "path": str(path),
        "name": path.name,
        "kind": kind,
        "duration_seconds": duration,
        "width": video.get("width") if isinstance(video.get("width"), int) else None,
        "height": video.get("height") if isinstance(video.get("height"), int) else None,
        "frame_rate": _fps(video) if video else None,
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "format": fmt.get("format_name"),
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "status": "ready",
    }


def inspect_reference(entry: dict) -> dict:
    """Rescan a saved reference; missing and unreadable files remain listed."""
    path = entry.get("path", "")
    try:
        return inspect_media(path)
    except (MediaProbeError, OSError) as exc:
        return {
            **entry,
            "status": "missing" if not Path(path).is_file() else "error",
            "error": str(exc),
        }

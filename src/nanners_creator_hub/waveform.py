"""Read-only PCM waveform peaks and narration-to-footage timing proposals."""
from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
import sys
from pathlib import Path


SAMPLE_RATE = 2000
MAX_WAVEFORM_DURATION = 900.0


@dataclass(frozen=True)
class Alignment:
    in_seconds: float
    out_seconds: float
    footage_seconds: float
    narration_seconds: float
    delta_seconds: float


def validate_sync_range(start: float, end: float, source_duration: float | None,
                        narration_duration: float) -> Alignment:
    if not all(math.isfinite(v) for v in (start, end, narration_duration)):
        raise ValueError("All time values must be finite.")
    if narration_duration <= 0:
        raise ValueError("Narration duration is not available.")
    if not 0 <= start < end <= 86400:
        raise ValueError("Select a valid footage IN and OUT point.")
    if source_duration is not None and (
        not math.isfinite(source_duration) or source_duration <= 0
        or end > source_duration + 0.05
    ):
        raise ValueError("Selected footage range exceeds the source recording.")
    return Alignment(
        round(start, 3), round(end, 3), round(end - start, 3),
        round(narration_duration, 3), round(end - start - narration_duration, 3)
    )


def suggested_out_point(start: float, narration_duration: float,
                        source_duration: float | None) -> float:
    if not math.isfinite(start) or start < 0:
        raise ValueError("Footage IN point is invalid.")
    if not math.isfinite(narration_duration) or narration_duration <= 0:
        raise ValueError("Narration duration must be positive.")
    proposed = round(start + narration_duration, 3)
    validate_sync_range(start, proposed, source_duration, narration_duration)
    return proposed


def ffmpeg_waveform_args(path: Path, *, sample_rate: int = SAMPLE_RATE) -> list[str]:
    """Small mono PCM stream for display; FFmpeg does not modify the source."""
    if not 200 <= sample_rate <= 8000:
        raise ValueError("Waveform sample rate is unsupported.")
    return [
        "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "s16le", "pipe:1",
    ]


def peaks_from_pcm(raw: bytes, *, bins: int = 420) -> tuple[float, ...]:
    """Convert little-endian signed PCM16 to bounded, normalized peak bins."""
    if not 1 <= bins <= 2000:
        raise ValueError("Waveform bin count is outside the supported range.")
    if not raw or len(raw) % 2:
        raise ValueError("Waveform data is missing or incomplete.")
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    length = len(samples)
    if length == 0:
        raise ValueError("The audio stream is empty.")
    peaks = []
    for index in range(bins):
        first = int(index * length / bins)
        last = min(length, max(first + 1, int((index + 1) * length / bins)))
        if first >= length:
            peaks.append(0.0)
            continue
        maximum = max(abs(v) for v in samples[first:last])
        peaks.append(min(1.0, maximum / 32768.0))
    return tuple(peaks)

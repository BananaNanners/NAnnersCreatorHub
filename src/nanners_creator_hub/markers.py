"""Frame-accurate, non-destructive Kdenlive timeline-marker export.

Kdenlive 26.08 uses [{"pos": FRAME_INDEX, "comment": "...", "type": 0}]
for JSON marker import/export. Positions are integer *timeline frames*, not seconds.
Our source sections are sequential planning assumptions, not a read of a .kdenlive edit.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from .projects import validate_project
from .sections import footage_duration

FRAME_RATES: dict[str, Fraction] = {
    "23.976 (24000/1001)": Fraction(24000, 1001),
    "24": Fraction(24),
    "25": Fraction(25),
    "29.97 (30000/1001)": Fraction(30000, 1001),
    "30": Fraction(30),
    "50": Fraction(50),
    "59.94 (60000/1001)": Fraction(60000, 1001),
    "60": Fraction(60),
}
TIMING_BASES = {"footage": "Selected footage ranges", "narration": "Narration durations"}


class MarkerPlanError(ValueError):
    """The source data cannot yield unambiguous sequential marker positions."""


def _round_frame(seconds: Fraction, rate: Fraction) -> int:
    # Round positive quantities to nearest frame; exact half rounded up.
    frame = seconds * rate
    return (2 * frame.numerator + frame.denominator) // (2 * frame.denominator)


def _section_duration(section: dict, library: dict, timing_basis: str) -> Fraction:
    if timing_basis == "footage":
        if not section.get("footage_path"):
            raise MarkerPlanError(f"{section['title']}: assign footage before exporting")
        span = footage_duration(section)
        entry = library.get(section["footage_path"])
        if span is None or span <= 0:
            raise MarkerPlanError(f"{section['title']}: select positive footage in/out range")
        if entry is None or entry.get("status") != "ready":
            raise MarkerPlanError(f"{section['title']}: footage reference needs inspection")
        if entry.get("kind") not in ("Video", "Video + Audio"):
            raise MarkerPlanError(f"{section['title']}: assigned footage has no video stream")
        total = entry.get("duration_seconds")
        if total is None or section["footage_out_seconds"] > total + 0.05:
            raise MarkerPlanError(f"{section['title']}: footage range exceeds/has unknown file duration")
        return Fraction(str(span))
    if timing_basis == "narration":
        if not section.get("narration_path"):
            raise MarkerPlanError(f"{section['title']}: assign narration before exporting")
        entry = library.get(section["narration_path"])
        if entry is None or entry.get("status") != "ready":
            raise MarkerPlanError(f"{section['title']}: narration reference needs inspection")
        if entry.get("kind") not in ("Audio", "Video + Audio"):
            raise MarkerPlanError(f"{section['title']}: assigned narration has no audio stream")
        seconds = entry.get("duration_seconds")
        if seconds is None or seconds <= 0:
            raise MarkerPlanError(f"{section['title']}: narration duration is unavailable")
        return Fraction(str(seconds))
    raise MarkerPlanError("Unknown timing basis")


def marker_plan(
    project: dict,
    fps_name: str = "30",
    timing_basis: str = "footage",
    starting_frame: int = 0,
) -> list[dict]:
    """Generate markers at section starts using a gapless *proposed* timeline."""
    validate_project(project)
    fps = FRAME_RATES.get(fps_name)
    if fps is None:
        raise MarkerPlanError("Unsupported project frame rate")
    if not isinstance(starting_frame, int) or isinstance(starting_frame, bool) or starting_frame < 0:
        raise MarkerPlanError("Starting frame must be a nonnegative integer")
    if timing_basis not in TIMING_BASES:
        raise MarkerPlanError("Unknown timing basis")
    sections = project["sections"]
    if not sections:
        raise MarkerPlanError("Add at least one section before exporting markers")
    media = {item["path"]: item for item in project.get("media", [])}
    running = Fraction(0)
    markers = []
    previous = -1
    for i, section in enumerate(sections, 1):
        position = starting_frame + _round_frame(running, fps)
        if position <= previous:
            raise MarkerPlanError(
                f"{section['title']}: this timing plan creates duplicate marker frames"
            )
        if position > 2_000_000_000:
            raise MarkerPlanError("Marker position exceeds supported frame range")
        markers.append({"pos": position, "comment": f"{i:02} — {section['title']}", "type": 0})
        previous = position
        running += _section_duration(section, media, timing_basis)
    return markers


def export_markers(
    path: str | Path,
    project: dict,
    fps_name: str = "30",
    timing_basis: str = "footage",
    starting_frame: int = 0,
) -> list[dict]:
    """Create JSON exclusively; never replace an existing file."""
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise MarkerPlanError("Kdenlive marker output must use .json")
    plan = marker_plan(project, fps_name, timing_basis, starting_frame)
    # Exclusive creation prevents overwrite even if an external process wins a race.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return plan

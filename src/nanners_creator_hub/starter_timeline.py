"""Experimental Kdenlive 26.08 starter timeline writer (new files only).

Writes an MLT-backed .kdenlive project with one video and one narration track,
a project bin, a sequence, and section-start guides. Excludes unconfirmed
sections and never modifies source recordings or an existing editing project.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import json
import os
import tempfile
from math import gcd
from pathlib import Path
from uuid import uuid4
import xml.etree.ElementTree as ET

from .markers import FRAME_RATES, _round_frame
from .projects import validate_project

MAX_SECTIONS = 100


class StarterTimelineError(ValueError):
    pass


@dataclass(frozen=True)
class TimelineClip:
    number: int
    title: str
    video: str
    narration: str
    timeline_in: int
    timeline_out: int
    video_source_in: int
    video_source_out: int
    audio_source_out: int
    narration_truncated: bool


@dataclass(frozen=True)
class TimelinePlan:
    clips: tuple[TimelineClip, ...]
    fps_name: str
    width: int
    height: int
    total_frames: int
    skipped: tuple[str, ...]


def _property(parent: ET.Element, name: str, value) -> None:
    ET.SubElement(parent, "property", {"name": name}).text = str(value)


def _valid_clip_media(entry: dict | None, kind: str, path: str) -> float:
    if not entry or entry.get("status") != "ready":
        raise StarterTimelineError(f"{kind}: media reference has not passed inspection")
    if kind == "Footage" and entry.get("kind") not in ("Video", "Video + Audio"):
        raise StarterTimelineError("Footage must contain a video stream")
    if kind == "Narration" and entry.get("kind") not in ("Audio", "Video + Audio"):
        raise StarterTimelineError("Narration must contain an audio stream")
    file = Path(path).expanduser()
    if not file.is_file():
        raise StarterTimelineError(f"{kind}: source file is missing: {file.name}")
    duration = entry.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
        raise StarterTimelineError(f"{kind}: valid file duration is required")
    return float(duration)


def plan_timeline(project: dict, fps_name: str = "60") -> TimelinePlan:
    validate_project(project)
    rate = FRAME_RATES.get(fps_name)
    if rate is None:
        raise StarterTimelineError("Choose a supported Kdenlive project frame rate")
    if len(project["sections"]) > MAX_SECTIONS:
        raise StarterTimelineError("Starter projects are limited to 100 sections")
    library = {entry["path"]: entry for entry in project["media"]}
    skipped = []
    clips = []
    running = 0
    width, height = 1920, 1080
    for i, section in enumerate(project["sections"], 1):
        if section["status"] != "confirmed":
            skipped.append(f"{i:02} {section['title']}: not Confirmed")
            continue
        title = section["title"]
        video = section["footage_path"]
        narration = section["narration_path"]
        if not video or not narration:
            raise StarterTimelineError(f"{title}: assign footage and narration first")
        footage_duration = _valid_clip_media(library.get(video), "Footage", video)
        audio_duration = _valid_clip_media(library.get(narration), "Narration", narration)
        start = Fraction(str(section["footage_in_seconds"]))
        end = Fraction(str(section["footage_out_seconds"]))
        if end <= start or float(end) > footage_duration + 0.001:
            raise StarterTimelineError(f"{title}: invalid footage source IN/OUT points")
        source_in = _round_frame(start, rate)
        source_out_exclusive = _round_frame(end, rate)
        segment_frames = source_out_exclusive - source_in
        if segment_frames <= 0:
            raise StarterTimelineError(f"{title}: footage range is shorter than one frame")
        audio_frames = _round_frame(Fraction(str(audio_duration)), rate)
        if audio_frames <= 0:
            raise StarterTimelineError(f"{title}: narration is shorter than one frame")
        actual_audio = min(audio_frames, segment_frames)
        if not clips:
            video_info = library[video]
            if all(isinstance(video_info.get(k), int) and video_info[k] > 0
                   for k in ("width", "height")):
                width, height = video_info["width"], video_info["height"]
        clips.append(TimelineClip(
            i, title, video, narration, running, running + segment_frames - 1,
            source_in, source_out_exclusive - 1, actual_audio - 1,
            audio_frames > segment_frames,
        ))
        running += segment_frames
    if not clips:
        raise StarterTimelineError(
            "No confirmed sections. Review your sections and set Review status to Confirmed."
        )
    if running > 2_000_000:
        raise StarterTimelineError("Starter timeline exceeds the supported frame limit")
    if width > 7680 or height > 4320:
        raise StarterTimelineError("Unusually large project dimensions; review footage")
    return TimelinePlan(tuple(clips), fps_name, width, height, running, tuple(skipped))


def _playlist_entry(playlist: ET.Element, producer: str,
                    start: int, end: int, clip_id: int) -> None:
    entry = ET.SubElement(playlist, "entry", {
        "producer": producer, "in": str(start), "out": str(end),
    })
    _property(entry, "kdenlive:id", clip_id)


def build_kdenlive_xml(plan: TimelinePlan, output_path: Path) -> bytes:
    rate = FRAME_RATES[plan.fps_name]
    sequence_uuid = "{" + str(uuid4()) + "}"
    doc_id = str(int(uuid4().int % 10**12))
    root = ET.Element("mlt", {
        "LC_NUMERIC": "C", "version": "7.25.0", "producer": "main_bin",
        "root": str(output_path.parent.resolve()),
    })
    ratio = gcd(plan.width, plan.height)
    ET.SubElement(root, "profile", {
        "description": f"{plan.width}x{plan.height}, {plan.fps_name} fps",
        "width": str(plan.width), "height": str(plan.height),
        "progressive": "1", "colorspace": "709",
        "sample_aspect_num": "1", "sample_aspect_den": "1",
        "display_aspect_num": str(plan.width // ratio),
        "display_aspect_den": str(plan.height // ratio),
        "frame_rate_num": str(rate.numerator),
        "frame_rate_den": str(rate.denominator),
    })
    black = ET.SubElement(root, "producer", {"id": "black_track", "in": "0",
                                            "out": str(plan.total_frames - 1)})
    for key, val in (
        ("resource", "black"), ("mlt_service", "color"),
        ("eof", "continue"), ("kdenlive:playlistid", "black_track"),
    ):
        _property(black, key, val)

    # Each unique source is one independent bin clip. Its original filepath is
    # absolute, so moving the starter project does not affect source resolution.
    paths = dict.fromkeys(
        path for clip in plan.clips for path in (clip.video, clip.narration)
    )
    chain_for: dict[str, tuple[str, int]] = {}
    for clip_id, source in enumerate(paths, 1):
        chain_id = f"source{clip_id}"
        chain_for[source] = (chain_id, clip_id)
        chain = ET.SubElement(root, "chain", {"id": chain_id})
        for key, val in (
            ("resource", str(Path(source).expanduser().resolve())),
            ("mlt_service", "avformat"),
            ("kdenlive:id", clip_id),
            ("kdenlive:clipname", Path(source).name),
            ("kdenlive:folderid", "0"),
            ("kdenlive:proxy", "-"),
        ):
            _property(chain, key, val)

    # One frame-accurate footage track (original recording audio is muted) and
    # one distinct narration track, both with two playlists for Kdenlive mixes.
    v0 = ET.SubElement(root, "playlist", {"id": "video_playlist"})
    ET.SubElement(root, "playlist", {"id": "video_mix"})
    a0 = ET.SubElement(root, "playlist", {"id": "narration_playlist"})
    ET.SubElement(root, "playlist", {"id": "narration_mix"})
    for clip in plan.clips:
        video_id, vid = chain_for[clip.video]
        narration_id, aud = chain_for[clip.narration]
        _playlist_entry(v0, video_id, clip.video_source_in,
                        clip.video_source_out, vid)
        _playlist_entry(a0, narration_id, 0, clip.audio_source_out, aud)
        footage_frames = clip.timeline_out - clip.timeline_in + 1
        narration_frames = clip.audio_source_out + 1
        if narration_frames < footage_frames:
            ET.SubElement(a0, "blank", {"length": str(
                footage_frames - narration_frames
            )})

    video_track = ET.SubElement(root, "tractor", {"id": "video_track",
                                                 "out": str(plan.total_frames - 1)})
    _property(video_track, "kdenlive:track_name", "V1 - Footage")
    _property(video_track, "kdenlive:timeline_active", "1")
    ET.SubElement(video_track, "track", {"producer": "video_playlist", "hide": "audio"})
    ET.SubElement(video_track, "track", {"producer": "video_mix", "hide": "audio"})

    audio_track = ET.SubElement(root, "tractor", {"id": "audio_track",
                                                 "out": str(plan.total_frames - 1)})
    _property(audio_track, "kdenlive:audio_track", 1)
    _property(audio_track, "kdenlive:track_name", "A1 - Narration")
    _property(audio_track, "kdenlive:timeline_active", "1")
    ET.SubElement(audio_track, "track", {"producer": "narration_playlist", "hide": "video"})
    ET.SubElement(audio_track, "track", {"producer": "narration_mix", "hide": "video"})

    sequence = ET.SubElement(root, "tractor", {
        "id": sequence_uuid, "in": "0", "out": str(plan.total_frames - 1),
    })
    for key, val in (
        ("kdenlive:uuid", sequence_uuid),
        ("kdenlive:clipname", "NAnners Starter Timeline"),
        ("kdenlive:sequenceproperties.hasVideo", "1"),
        ("kdenlive:sequenceproperties.hasAudio", "1"),
        ("kdenlive:sequenceproperties.tracks", "2"),
        ("kdenlive:sequenceproperties.tracksCount", "2"),
        ("kdenlive:sequenceproperties.activeTrack", "2"),
        ("kdenlive:sequenceproperties.videoTarget", "2"),
        ("kdenlive:sequenceproperties.audioTarget", "1"),
        ("kdenlive:sequenceproperties.documentuuid", sequence_uuid),
        ("kdenlive:sequenceproperties.groups", "[]"),
        ("kdenlive:id", len(paths) + 1),
        ("kdenlive:clip_type", "0"),
        ("kdenlive:producer_type", "17"),
        ("kdenlive:folderid", "1"),
    ):
        _property(sequence, key, val)
    _property(sequence, "kdenlive:sequenceproperties.guides", json.dumps([
        {"pos": clip.timeline_in, "comment": f"{clip.number:02} — {clip.title}", "type": 0}
        for clip in plan.clips
    ], ensure_ascii=False))
    ET.SubElement(sequence, "track", {"producer": "black_track"})
    ET.SubElement(sequence, "track", {"producer": "audio_track", "hide": "video"})
    ET.SubElement(sequence, "track", {"producer": "video_track", "hide": "audio"})
    transition = ET.SubElement(sequence, "transition", {"id": "audio_mix_transition"})
    for key, val in (
        ("a_track", 0), ("b_track", 1), ("mlt_service", "mix"),
        ("always_active", 1), ("sum", 1), ("accepts_blanks", 1),
        ("internal_added", 237),
    ):
        _property(transition, key, val)
    overlay = ET.SubElement(sequence, "transition", {"id": "video_mix_transition"})
    for key, val in (
        ("a_track", 0), ("b_track", 2), ("mlt_service", "qtblend"),
        ("always_active", 1), ("internal_added", 237),
    ):
        _property(overlay, key, val)

    bin_playlist = ET.SubElement(root, "playlist", {"id": "main_bin"})
    for key, val in (
        ("kdenlive:folder.-1.1", "Sequences"),
        ("kdenlive:sequenceFolder", "1"),
        ("kdenlive:docproperties.audioChannels", "2"),
        ("kdenlive:docproperties.documentid", doc_id),
        ("kdenlive:docproperties.version", "1.1"),
        ("kdenlive:docproperties.kdenliveversion", "26.08.3"),
        ("kdenlive:docproperties.uuid", sequence_uuid),
        ("kdenlive:docproperties.opensequences", sequence_uuid),
        ("kdenlive:docproperties.activetimeline", sequence_uuid),
        ("xml_retain", "1"),
    ):
        _property(bin_playlist, key, val)
    for source, (producer, _number) in chain_for.items():
        ET.SubElement(bin_playlist, "entry", {
            "producer": producer, "in": "0", "out": "0",
        })
    ET.SubElement(bin_playlist, "entry", {
        "producer": sequence_uuid, "in": "0", "out": "0",
    })
    end = ET.SubElement(root, "tractor", {
        "id": "final_tractor", "in": "0", "out": str(plan.total_frames - 1),
    })
    _property(end, "kdenlive:projectTractor", "1")
    ET.SubElement(end, "track", {
        "producer": sequence_uuid, "in": "0",
        "out": str(plan.total_frames - 1),
    })
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def export_starter_timeline(path: Path, project: dict, fps_name: str = "60") -> TimelinePlan:
    target = Path(path)
    if target.suffix.lower() != ".kdenlive":
        raise StarterTimelineError("Output must be a new .kdenlive project")
    plan = plan_timeline(project, fps_name)
    xml = build_kdenlive_xml(plan, target)
    # Write a complete file to a sibling staging path, then publish using a
    # no-overwrite hard link; never expose a partially written .kdenlive file.
    ET.fromstring(xml)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".nanners-starter-", suffix=".tmp",
            dir=target.parent, delete=False,
        ) as out:
            stage = Path(out.name)
            out.write(xml)
            out.flush()
            os.fsync(out.fileno())
        os.link(stage, target)
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)
    return plan

"""Non-destructive Kokoro narration job preparation and publication.

Only exports *new* WAV/TXT take pairs; never replaces files. The CLI itself
runs separately in QProcess, with the input and output staged locally.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .kokoro import validate_preferences


@dataclass(frozen=True)
class NarrationJob:
    work_dir: Path
    input_script: Path
    original_script: Path
    temporary_wav: Path
    output_dir: Path
    stem: str
    voice: str
    language: str
    speed: float
    model: Path
    voices: Path


def safe_stem(label: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", label.strip()).strip("-_")[:60]
    return slug or "narration"


def prepare_job(script: str, label: str, output_dir: Path, prefs: dict, spoken_script: str | None = None) -> NarrationJob:
    prefs = validate_preferences(prefs)
    if not isinstance(script, str) or not script.strip():
        raise ValueError("Write or paste a narration script first.")
    if len(script) > 60_000:
        raise ValueError("Script is too long (60,000-character limit). Split it into sections.")
    if spoken_script is None:
        spoken_script = script
    if not isinstance(spoken_script, str) or not spoken_script.strip() or len(spoken_script) > 60_000:
        raise ValueError("Speech-ready script is missing or too long.")
    output_dir = Path(output_dir).expanduser()
    if not output_dir.is_dir():
        output_dir.mkdir(parents=True, exist_ok=True)
    if not output_dir.is_dir():
        raise ValueError("Narration output is not a directory.")
    folder = Path(tempfile.mkdtemp(dir=output_dir, prefix=".nanners-tts-"))
    script_file = folder / "narration-script.txt"
    original_file = folder / "original-script.txt"
    try:
        original_file.write_text(script, encoding="utf-8")
        script_file.write_text(spoken_script, encoding="utf-8")
        return NarrationJob(
            folder, script_file, original_file, folder / "narration-generated.wav",
            output_dir, safe_stem(label), prefs["voice"], prefs["language"],
            prefs["speed"], Path(prefs["model_path"]).expanduser(),
            Path(prefs["voices_path"]).expanduser(),
        )
    except BaseException:
        shutil.rmtree(folder)
        raise


def kokoro_arguments(job: NarrationJob) -> list[str]:
    return [
        str(job.input_script), str(job.temporary_wav),
        "--model", str(job.model),
        "--voices", str(job.voices),
        "--voice", job.voice,
        "--lang", job.language,
        "--speed", str(job.speed),
        "--format", "wav",
    ]


def validate_wav(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 44:
        raise ValueError("Kokoro did not create a usable WAV file.")
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                raise ValueError("Kokoro created an empty WAV file.")
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError(f"Kokoro output was not a valid PCM WAV: {exc}") from exc


def publish_take(job: NarrationJob) -> Path:
    """Atomically link new files; refuse replacing existing files."""
    validate_wav(job.temporary_wav)
    for _ in range(30):
        suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
        identity = uuid.uuid4().hex[:8]
        base = f"{job.stem}-{suffix}-{identity}"
        wav_target = job.output_dir / f"{base}.wav"
        text_target = job.output_dir / f"{base}.txt"
        try:
            os.link(job.temporary_wav, wav_target)
        except FileExistsError:
            continue
        created = [wav_target]
        try:
            os.link(job.original_script, text_target)
            created.append(text_target)
        except BaseException:
            for created_path in created:
                created_path.unlink(missing_ok=True)
            raise
        return wav_target
    raise FileExistsError("Could not select a unique narration filename.")


def cleanup_job(job: NarrationJob | None) -> None:
    if job is not None:
        shutil.rmtree(job.work_dir, ignore_errors=True)

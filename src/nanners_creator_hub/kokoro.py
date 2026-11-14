"""Read-only Kokoro discovery and per-user narration preferences.

Dev1 does not synthesize audio or modify models, voices or recordings.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

MODEL_NAME = "kokoro-v1.0.onnx"
VOICES_NAME = "voices-v1.0.bin"
DEFAULT_VOICE = "em_alex"
LANGUAGES = ("en-us", "en-gb", "fr-fr", "it", "ja", "cmn")
PREFERENCE_VERSION = 1


@dataclass(frozen=True)
class KokoroStatus:
    executable: str | None
    model_path: Path
    voices_path: Path
    available_voices: tuple[str, ...]
    problems: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.problems


def default_models_folder() -> Path:
    return Path.home() / "Applications" / "kokoro-tts"


def preferences_path() -> Path:
    data_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    return data_home / "nanners-creator-hub" / "kokoro.json"


def default_preferences() -> dict:
    folder = default_models_folder()
    return {
        "schema_version": PREFERENCE_VERSION,
        "model_path": str(folder / MODEL_NAME),
        "voices_path": str(folder / VOICES_NAME),
        "voice": DEFAULT_VOICE,
        "language": "en-gb",
        "speed": 1.0,
    }


def validate_preferences(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema_version") != PREFERENCE_VERSION:
        raise ValueError("Unsupported Kokoro settings format")
    result = dict(default_preferences())
    for field in ("model_path", "voices_path"):
        val = data.get(field)
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Invalid {field}")
        result[field] = val
    voice = data.get("voice")
    if not isinstance(voice, str) or not voice or not voice.replace("_", "").isalnum():
        raise ValueError("Invalid voice selection")
    result["voice"] = voice
    if data.get("language") not in LANGUAGES:
        raise ValueError("Unsupported Kokoro language")
    result["language"] = data["language"]
    speed = data.get("speed")
    if isinstance(speed, bool) or not isinstance(speed, (float, int)) or not (0.5 <= speed <= 2.0):
        raise ValueError("Speed must be between 0.5 and 2.0")
    result["speed"] = float(speed)
    return result


def load_preferences(path: Path | None = None) -> dict:
    target = path if path is not None else preferences_path()
    if not target.is_file():
        return default_preferences()
    return validate_preferences(json.loads(target.read_text(encoding="utf-8")))


def save_preferences(prefs: dict, path: Path | None = None) -> Path:
    """Atomically write a separate config, never a user's tutorial or model files."""
    data = validate_preferences(prefs)
    target = path if path is not None else preferences_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent,
                                         prefix=".kokoro-", suffix=".tmp", delete=False) as handle:
            stage = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(stage, target)
        stage = None
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)
    return target


def discover_voices(path: Path) -> tuple[str, ...]:
    """List voice names from NumPy ZIP members, without loading tensors or executing code."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = {
                Path(item.filename).stem
                for item in archive.infolist()
                if not item.is_dir()
                and "/" not in item.filename
                and item.filename.endswith(".npy")
                and not item.filename.startswith(".")
            }
            if len(names) > 1000:
                raise ValueError("Voice archive has too many entries")
            return tuple(sorted(n for n in names if n.replace("_", "").isalnum()))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Cannot inspect Kokoro voices: {exc}") from exc


def inspect_kokoro(prefs: dict, executable: str | None = None) -> KokoroStatus:
    prefs = validate_preferences(prefs)
    exe = executable if executable is not None else shutil.which("kokoro-tts")
    model = Path(prefs["model_path"]).expanduser()
    voices_path = Path(prefs["voices_path"]).expanduser()
    problems = []
    voices = ()
    if not exe or not Path(exe).is_file():
        problems.append("kokoro-tts executable not found on PATH")
    if not model.is_file() or model.stat().st_size == 0:
        problems.append("Kokoro ONNX model file missing or empty")
    if not voices_path.is_file() or voices_path.stat().st_size == 0:
        problems.append("Kokoro voices file missing or empty")
    else:
        try:
            voices = discover_voices(voices_path)
            if not voices:
                problems.append("Voice archive contains no named voices")
        except ValueError as exc:
            problems.append(str(exc))
    if voices and prefs["voice"] not in voices:
        problems.append(f"Selected voice {prefs['voice']} not in the voice archive")
    return KokoroStatus(exe, model, voices_path, voices, tuple(problems))

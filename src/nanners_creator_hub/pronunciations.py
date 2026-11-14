"""Editable, local Kokoro speech-pronunciation rules.

Rules only transform a generated speech copy; original scripts remain unchanged.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

VERSION = 1
DEFAULT_RULES = (("NAnners", "Nanners"), ("Wineland", "Wine land"))


def rules_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    return config_home / "nanners-creator-hub" / "pronunciations.json"


def validate_rules(rules) -> tuple[tuple[str, str], ...]:
    if not isinstance(rules, (tuple, list)) or len(rules) > 100:
        raise ValueError("Pronunciation list must contain at most 100 rules")
    validated = []
    seen = set()
    for pair in rules:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("Each pronunciation rule needs an original and spoken form")
        original, spoken = pair
        if not all(isinstance(s, str) and 0 < len(s.strip()) <= 100 for s in pair):
            raise ValueError("Pronunciation entries must be 1–100 characters long")
        if "\n" in original or "\n" in spoken or "=>" in original:
            raise ValueError("Rules cannot contain newlines or '=>' in the original text")
        if original.casefold() in seen:
            raise ValueError(f"Duplicate pronunciation rule for {original!r}")
        seen.add(original.casefold())
        validated.append((original.strip(), spoken.strip()))
    return tuple(validated)


def parse_rules(text: str) -> tuple[tuple[str, str], ...]:
    rules = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if "=>" not in line:
            raise ValueError(f"Line {line_no}: use Original => Spoken")
        original, spoken = [part.strip() for part in line.split("=>", 1)]
        rules.append((original, spoken))
    return validate_rules(rules)


def render_rules(rules) -> str:
    return "\n".join(f"{source} => {spoken}" for source, spoken in validate_rules(rules))


def speech_text(script: str, rules) -> str:
    if not isinstance(script, str):
        raise ValueError("Script must be text")
    result = script
    for original, spoken in validate_rules(rules):
        # Match standalone words/phrases only; avoid changing NAnnersVRhub.
        pattern = re.compile(r"(?<!\w)" + re.escape(original) + r"(?!\w)", re.IGNORECASE)
        result = pattern.sub(lambda _match: spoken, result)
    return result


def load_rules(path: Path | None = None) -> tuple[tuple[str, str], ...]:
    target = path if path is not None else rules_path()
    if not target.is_file():
        return DEFAULT_RULES
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != VERSION:
        raise ValueError("Unsupported pronunciation settings format")
    return validate_rules(data.get("rules"))


def save_rules(rules, path: Path | None = None) -> Path:
    target = path if path is not None else rules_path()
    cleaned = validate_rules(rules)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=target.parent,
            prefix=".pronunciation-", suffix=".tmp", delete=False
        ) as handle:
            temp = Path(handle.name)
            json.dump({"schema_version": VERSION, "rules": cleaned}, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
        temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return target

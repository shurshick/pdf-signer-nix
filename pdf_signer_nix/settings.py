from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import StampSettings
from .paths import settings_path


def default_settings() -> dict:
    return {
        "version": 1,
        "last_output_dir": str(Path.home() / "Documents" / "Signed PDFs"),
        "save_next_to_source": True,
        "create_detached_sig": False,
        "detached_only": False,
        "verify_after_signing": False,
        "stamp": asdict(StampSettings()),
    }


def load_settings(path: Path | None = None) -> dict:
    target = path or settings_path()
    if not target.exists():
        return default_settings()
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default_settings()
    merged = default_settings()
    deep_update(merged, loaded)
    return merged


def save_settings(settings: dict, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def export_settings(target: Path, settings: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"app": "pdf-signer-nix", "settings": settings}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def import_settings(source: Path, current: dict) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    candidate = payload.get("settings", payload) if isinstance(payload, dict) else None
    if not isinstance(candidate, dict):
        raise ValueError("Settings JSON has unsupported format")
    merged = default_settings()
    deep_update(merged, candidate)
    return merged


def deep_update(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value

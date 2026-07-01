from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from . import __version__
from .models import StampSettings, builtin_stamp_settings
from .paths import settings_path


WINDOWS_PROFILE_NAMES = {
    "ГОСТ минимальный": "gost-minimal",
    "ГОСТ стандартный": "gost-standard",
    "ГОСТ подробный": "gost-detailed",
}


def default_settings() -> dict:
    return {
        "version": 2,
        "last_output_dir": str(Path.home() / "Documents" / "Signed PDFs"),
        "save_next_to_source": True,
        "signature_mode": "embedded",
        "verify_after_signing": False,
        "verification_view": "summary",
        "stamp": stamp_to_payload(StampSettings()),
    }


def load_settings(path: Path | None = None) -> dict:
    target = path or settings_path()
    if not target.exists():
        return default_settings()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default_settings()
    return merge_settings(payload)


def save_settings(settings: dict, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = merge_settings(settings)
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def export_settings(target: Path, settings: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = merge_settings(settings)
    payload = {
        "app": "pdf-signer-nix",
        "appVersion": __version__,
        "exportedAtUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "settings": normalized,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def import_settings(source: Path, current: dict) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    candidate = unwrap_settings_payload(payload)
    return merge_settings(candidate)


def merge_settings(payload: Any) -> dict:
    merged = default_settings()
    candidate = unwrap_settings_payload(payload)

    if isinstance(candidate, dict) and any(key in candidate for key in ("StampProfile", "LastStampProfileName", "VerifyAfterSigning")):
        candidate = from_windows_settings(candidate)
    elif isinstance(candidate, dict) and any(key in candidate for key in ("templateName", "positionMode", "customX", "customY")):
        candidate = {"stamp": stamp_to_payload(stamp_from_payload(candidate))}

    if not isinstance(candidate, dict):
        return merged

    deep_update(merged, candidate)
    merged["signature_mode"] = _normalize_signature_mode(merged)
    merged["stamp"] = stamp_to_payload(stamp_from_payload(merged.get("stamp", {})))
    return merged


def unwrap_settings_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        if isinstance(payload.get("settings"), dict):
            return payload["settings"]
        if isinstance(payload.get("stamp"), dict):
            return payload
    return payload


def deep_update(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value


def stamp_from_payload(payload: dict[str, Any] | StampSettings) -> StampSettings:
    if isinstance(payload, StampSettings):
        return payload.clone().normalize()

    builtin = builtin_stamp_settings()
    source = dict(payload or {})
    template_name = str(source.get("template_name") or source.get("templateName") or "").strip()
    size_mode = str(source.get("size_mode") or source.get("sizeMode") or "").strip()
    preset_name = str(source.get("name") or "").strip()

    if not template_name:
        template_name = WINDOWS_PROFILE_NAMES.get(preset_name, "")
    if template_name in builtin:
        stamp = builtin[template_name].clone()
    elif size_mode in builtin:
        stamp = builtin[size_mode].clone()
    else:
        stamp = StampSettings()

    stamp.name = source.get("name", stamp.name)
    stamp.template_name = source.get("template_name", source.get("templateName", stamp.template_name))
    stamp.size_mode = source.get("size_mode", source.get("sizeMode", stamp.size_mode))
    stamp.page_mode = source.get("page_mode", source.get("pageMode", stamp.page_mode))
    stamp.specific_page = int(source.get("specific_page", source.get("SpecificPage", stamp.specific_page)) or stamp.specific_page)
    stamp.position = source.get("position", source.get("positionMode", stamp.position))
    stamp.auto_place = bool(source.get("auto_place", source.get("autoPlace", stamp.auto_place)))
    stamp.x = float(source.get("x", source.get("customX", stamp.x)) or stamp.x)
    stamp.y = float(source.get("y", source.get("customY", stamp.y)) or stamp.y)
    stamp.margin = float(source.get("margin", source.get("Margin", stamp.margin)) or stamp.margin)
    stamp.width_mm = float(source.get("width_mm", source.get("widthMm", stamp.width_mm)) or stamp.width_mm)
    stamp.height_mm = float(source.get("height_mm", source.get("heightMm", stamp.height_mm)) or stamp.height_mm)
    stamp.opacity = _parse_opacity(source.get("opacity", source.get("OpacityPercent", stamp.opacity)))
    stamp.font_size = float(source.get("font_size", source.get("fontSize", stamp.font_size)) or stamp.font_size)
    stamp.min_font_size = float(source.get("min_font_size", source.get("minFontSize", stamp.min_font_size)) or stamp.min_font_size)
    stamp.reason = str(source.get("reason", stamp.reason))
    stamp.include_owner = bool(source.get("include_owner", source.get("IncludeOwner", stamp.include_owner)))
    stamp.include_organization = bool(source.get("include_organization", source.get("showOrganization", source.get("IncludeOrganization", stamp.include_organization))))
    stamp.include_position = bool(source.get("include_position", source.get("showPosition", source.get("IncludePosition", stamp.include_position))))
    stamp.include_inn = bool(source.get("include_inn", source.get("showInn", source.get("IncludeInn", stamp.include_inn))))
    stamp.include_snils = bool(source.get("include_snils", source.get("showSnils", source.get("IncludeSnils", stamp.include_snils))))
    stamp.include_issuer = bool(source.get("include_issuer", source.get("showIssuer", source.get("IncludeIssuer", stamp.include_issuer))))
    stamp.include_serial = bool(source.get("include_serial", source.get("IncludeSerialNumber", stamp.include_serial)))
    stamp.include_thumbprint = bool(source.get("include_thumbprint", source.get("showThumbprint", source.get("IncludeThumbprint", stamp.include_thumbprint))))
    stamp.include_reason = bool(source.get("include_reason", source.get("showReason", source.get("IncludeReason", stamp.include_reason))))
    stamp.include_date = bool(source.get("include_date", source.get("IncludeDate", stamp.include_date)))
    stamp.include_time = bool(source.get("include_time", source.get("IncludeTime", stamp.include_time)))
    stamp.include_signing_date_time = bool(
        source.get("include_signing_date_time", source.get("showSigningDateTime", source.get("IncludeSigningDateTime", stamp.include_signing_date_time)))
    )
    stamp.include_custom_text = bool(source.get("include_custom_text", source.get("IncludeCustomText", stamp.include_custom_text)))
    stamp.custom_text = str(source.get("custom_text", source.get("customText", stamp.custom_text)) or "")
    stamp.logo_path = str(source.get("logo_path", source.get("logoPath", stamp.logo_path)) or "")
    stamp.logo_scale = _parse_logo_scale(source.get("logo_scale", source.get("logoScalePercent", stamp.logo_scale)))
    return stamp.normalize()


def stamp_to_payload(stamp: StampSettings) -> dict[str, Any]:
    normalized = stamp.clone().normalize()
    data = asdict(normalized)
    data["opacity"] = round(normalized.opacity, 3)
    data["logo_scale"] = round(normalized.logo_scale, 3)
    return data


def from_windows_settings(settings: dict[str, Any]) -> dict:
    stamp = stamp_from_payload(settings.get("StampProfile", {}))
    return {
        "signature_mode": "embedded",
        "verify_after_signing": bool(settings.get("VerifyAfterSigning", False)),
        "verification_view": str(settings.get("VerificationView", "summary")).lower(),
        "stamp": stamp_to_payload(stamp),
    }


def _normalize_signature_mode(settings: dict[str, Any]) -> str:
    if bool(settings.get("detached_only")) or bool(settings.get("create_detached_sig")):
        return "detached"
    mode = str(settings.get("signature_mode", "")).strip().lower()
    if mode in {"embedded", "detached"}:
        return mode
    return "embedded"


def save_stamp_profile(target: Path, stamp: StampSettings) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(stamp_to_payload(stamp), ensure_ascii=False, indent=2), encoding="utf-8")


def load_stamp_profile(source: Path) -> StampSettings:
    payload = json.loads(source.read_text(encoding="utf-8"))
    return stamp_from_payload(payload)


def _parse_opacity(value: Any) -> float:
    if isinstance(value, (int, float)):
        if value > 1:
            return min(1.0, max(0.0, float(value) / 100.0))
        return min(1.0, max(0.0, float(value)))
    return 1.0


def _parse_logo_scale(value: Any) -> float:
    if isinstance(value, (int, float)):
        if value > 3:
            return min(3.0, max(0.1, float(value) / 100.0))
        return min(3.0, max(0.1, float(value)))
    return 1.0

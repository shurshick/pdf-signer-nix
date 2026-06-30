from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR_NAME = "PDF Signer Nix"


def data_dir() -> Path:
    override = os.environ.get("PDF_SIGNER_NIX_DATA_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def config_dir() -> Path:
    override = os.environ.get("PDF_SIGNER_NIX_CONFIG_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".config" / APP_DIR_NAME


def log_dir() -> Path:
    return data_dir() / "logs"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def app_root_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def asset_path(name: str) -> Path:
    return app_root_dir() / "assets" / name


def installed_icon_path() -> Path:
    return Path("/usr/share/icons/hicolor/512x512/apps/pdf-signer-nix.png")

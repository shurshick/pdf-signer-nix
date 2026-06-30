from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.request import Request, urlopen

from . import __version__


LATEST_RELEASE_API_URL = "https://api.github.com/repos/shurshick/pdf-signer-nix/releases/latest"


@dataclass(slots=True)
class ReleaseInfo:
    tag_name: str
    url: str


def get_current_version_text() -> str:
    return __version__


def is_newer_than_current(tag_name: str) -> bool:
    latest = parse_version(tag_name)
    current = parse_version(__version__)
    return latest > current


def parse_version(value: str) -> tuple[int, ...]:
    normalized = (value or "").strip()
    if normalized.lower().startswith("v"):
        normalized = normalized[1:]
    parts: list[int] = []
    for item in normalized.split("."):
        if item.isdigit():
            parts.append(int(item))
        else:
            break
    return tuple(parts)


def get_latest_release(timeout: int = 10) -> ReleaseInfo:
    request = Request(
        LATEST_RELEASE_API_URL,
        headers={
            "User-Agent": "PDF Signer Nix",
            "Accept": "application/vnd.github+json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag_name = str(payload.get("tag_name", "")).strip()
    url = str(payload.get("html_url", "")).strip()
    if not tag_name or not url:
        raise RuntimeError("GitHub не вернул данные релиза.")
    return ReleaseInfo(tag_name=tag_name, url=url)

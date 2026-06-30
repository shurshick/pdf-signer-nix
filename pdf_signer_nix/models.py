from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


StampPosition = Literal["bottom-right", "bottom-left", "top-right", "top-left", "custom"]
StampPageMode = Literal["all", "first", "last", "specific"]


@dataclass(slots=True)
class Certificate:
    subject: str = ""
    issuer: str = ""
    serial: str = ""
    thumbprint: str = ""
    container: str = ""
    provider: str = ""
    not_before: str = ""
    not_after: str = ""
    has_private_key: bool | None = None

    @property
    def owner(self) -> str:
        return extract_dn_part(self.subject, "CN") or self.subject

    @property
    def organization(self) -> str:
        return extract_dn_part(self.subject, "O")

    @property
    def label(self) -> str:
        parts = [self.owner]
        if self.organization:
            parts.append(self.organization)
        if self.not_after:
            parts.append(f"до {self.not_after}")
        if self.thumbprint:
            parts.append(self.thumbprint[-12:])
        return " | ".join(p for p in parts if p)


@dataclass(slots=True)
class StampSettings:
    page_mode: StampPageMode = "all"
    specific_page: int = 1
    position: StampPosition = "bottom-right"
    auto_place: bool = True
    x: float = 36.0
    y: float = 36.0
    width_mm: float = 90.0
    height_mm: float = 35.0
    opacity: float = 0.82
    reason: str = "Подписано в PDF Signer Nix"
    include_owner: bool = True
    include_issuer: bool = True
    include_serial: bool = True
    include_thumbprint: bool = True
    include_reason: bool = True
    include_date: bool = True
    logo_path: str = ""
    logo_scale: float = 1.0


@dataclass(slots=True)
class SigningJob:
    pdf_paths: list[Path]
    output_dir: Path
    certificate: Certificate
    stamp: StampSettings = field(default_factory=StampSettings)
    detached_only: bool = False
    create_detached_sig: bool = False
    save_next_to_source: bool = True
    verify_after_signing: bool = False


@dataclass(slots=True)
class SigningResult:
    source_pdf: Path
    output_pdf: Path
    signature_path: Path | None
    embedded: bool
    verified: bool | None = None
    message: str = ""


def extract_dn_part(value: str, key: str) -> str:
    marker = key.upper() + "="
    for raw in value.split(","):
        part = raw.strip()
        if part.upper().startswith(marker):
            return part[len(marker) :].strip()
    return ""

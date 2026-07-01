from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal


StampPosition = Literal["bottom-right", "bottom-left", "top-right", "top-left", "custom"]
StampPageMode = Literal["all", "first", "last", "specific"]
StampTemplateName = Literal["gost-minimal", "gost-standard", "gost-detailed", "custom"]
StampSizeMode = Literal["minimal", "standard", "detailed", "custom"]
VerificationStatus = Literal["VALID", "WARNING", "INVALID"]
SignatureMode = Literal["embedded", "detached"]


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
    def position(self) -> str:
        return extract_dn_part(self.subject, "T")

    @property
    def inn(self) -> str:
        return extract_dn_part(self.subject, "ИНН")

    @property
    def snils(self) -> str:
        return extract_dn_part(self.subject, "СНИЛС")

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
    name: str = "ГОСТ стандартный"
    template_name: StampTemplateName = "gost-standard"
    size_mode: StampSizeMode = "standard"
    page_mode: StampPageMode = "last"
    specific_page: int = 1
    position: StampPosition = "bottom-right"
    auto_place: bool = False
    x: float = 36.0
    y: float = 36.0
    margin: float = 36.0
    width_mm: float = 90.0
    height_mm: float = 35.0
    opacity: float = 1.0
    font_size: float = 7.0
    min_font_size: float = 7.0
    reason: str = "Подписано в PDF Signer Nix"
    include_owner: bool = True
    include_organization: bool = False
    include_position: bool = False
    include_inn: bool = False
    include_snils: bool = False
    include_issuer: bool = False
    include_serial: bool = True
    include_thumbprint: bool = False
    include_reason: bool = False
    include_date: bool = False
    include_time: bool = False
    include_signing_date_time: bool = False
    include_custom_text: bool = False
    custom_text: str = ""
    logo_path: str = ""
    logo_scale: float = 1.0

    def clone(self) -> "StampSettings":
        return replace(self)

    def normalize(self) -> "StampSettings":
        if self.specific_page < 1:
            self.specific_page = 1
        self.margin = max(0.0, self.margin)
        self.opacity = min(1.0, max(0.0, self.opacity))
        self.min_font_size = max(6.0, self.min_font_size)
        self.font_size = max(self.min_font_size, self.font_size or self.min_font_size)
        self.logo_scale = min(3.0, max(0.1, self.logo_scale or 1.0))
        self.custom_text = (self.custom_text or "").strip()

        if self.template_name == "gost-minimal" or self.size_mode == "minimal":
            self.name = "ГОСТ минимальный"
            self.template_name = "gost-minimal"
            self.size_mode = "minimal"
            self.width_mm = 70.0
            self.height_mm = 25.0
            self.min_font_size = max(6.0, self.min_font_size)
            self.font_size = max(self.min_font_size, min(self.font_size, 7.0))
        elif self.template_name == "gost-detailed" or self.size_mode == "detailed":
            self.name = "ГОСТ подробный"
            self.template_name = "gost-detailed"
            self.size_mode = "detailed"
            self.width_mm = 120.0
            self.height_mm = 45.0
            self.min_font_size = max(7.0, self.min_font_size)
            self.font_size = max(self.min_font_size, self.font_size)
        elif self.template_name == "custom" or self.size_mode == "custom":
            self.template_name = "custom"
            self.size_mode = "custom"
            self.width_mm = max(60.0, self.width_mm)
            self.height_mm = max(20.0, self.height_mm)
            self.min_font_size = max(6.0, self.min_font_size)
            self.font_size = max(self.min_font_size, self.font_size)
            if not self.name.strip():
                self.name = "Custom"
        else:
            self.name = "ГОСТ стандартный"
            self.template_name = "gost-standard"
            self.size_mode = "standard"
            self.width_mm = 90.0
            self.height_mm = 35.0
            self.min_font_size = max(7.0, self.min_font_size)
            self.font_size = max(self.min_font_size, self.font_size)
        return self

    @property
    def width_points(self) -> float:
        return self.width_mm * 72.0 / 25.4

    @property
    def height_points(self) -> float:
        return self.height_mm * 72.0 / 25.4


@dataclass(slots=True)
class SigningJob:
    pdf_paths: list[Path]
    output_dir: Path
    certificate: Certificate
    stamp: StampSettings = field(default_factory=StampSettings)
    signature_mode: SignatureMode = "embedded"
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


@dataclass(slots=True)
class SignatureCertificateDetails:
    subject: str = ""
    issuer: str = ""
    serial_number: str = ""
    thumbprint: str = ""
    signature_algorithm: str = ""
    not_before: str = ""
    not_after: str = ""


@dataclass(slots=True)
class VerificationReport:
    file_path: Path
    format: str
    status: VerificationStatus = "WARNING"
    status_description: str = "Проверка еще не выполнена."
    signature_exists: bool = False
    signature_container_valid: bool = False
    pdf_readable: bool = False
    signing_date: str = ""
    has_timestamp: bool = False
    certificate_chain_status: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    certificate: SignatureCertificateDetails = field(default_factory=SignatureCertificateDetails)
    raw_output: str = ""


def extract_dn_part(value: str, key: str) -> str:
    key_upper = key.upper()
    aliases = {key_upper}
    if key_upper == "ИНН":
        aliases.add("INN")
    elif key_upper == "СНИЛС":
        aliases.add("SNILS")
    marker_variants = [alias + "=" for alias in aliases]
    for raw in value.split(","):
        part = raw.strip()
        upper = part.upper()
        for marker in marker_variants:
            if upper.startswith(marker):
                return part[len(marker) :].strip()
    return ""


def builtin_stamp_settings() -> dict[str, StampSettings]:
    return {
        "gost-minimal": StampSettings(
            name="ГОСТ минимальный",
            template_name="gost-minimal",
            size_mode="minimal",
            include_organization=False,
            include_position=False,
            include_inn=False,
            include_snils=False,
            include_thumbprint=False,
            include_issuer=False,
            include_reason=False,
            include_signing_date_time=False,
        ).normalize(),
        "gost-standard": StampSettings(
            name="ГОСТ стандартный",
            template_name="gost-standard",
            size_mode="standard",
            include_reason=False,
            include_thumbprint=False,
            include_signing_date_time=False,
        ).normalize(),
        "gost-detailed": StampSettings(
            name="ГОСТ подробный",
            template_name="gost-detailed",
            size_mode="detailed",
            include_organization=True,
            include_inn=True,
            include_snils=True,
            include_thumbprint=True,
            include_issuer=True,
            include_reason=True,
            include_signing_date_time=False,
        ).normalize(),
    }

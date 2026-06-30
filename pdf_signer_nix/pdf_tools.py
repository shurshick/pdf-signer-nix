from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import portrait
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .models import Certificate, StampSettings

POINTS_PER_MM = 72.0 / 25.4
STAMP_BLUE = Color(0 / 255, 74 / 255, 173 / 255)


@dataclass(slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height

    def intersects(self, other: "Rect") -> bool:
        return self.x < other.right and self.right > other.x and self.y < other.top and self.top > other.y


@dataclass(slots=True)
class StampLayoutResult:
    font_size: float
    wrapped_lines: list[str]
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def stamp_pdf(input_pdf: Path, output_pdf: Path, cert: Certificate, settings: StampSettings) -> Path:
    settings = settings.clone().normalize()
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()
    page_indexes = selected_pages(len(reader.pages), settings)
    for index, page in enumerate(reader.pages):
        if index in page_indexes:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            stamp_rect = choose_stamp_rect(page, width, height, settings)
            overlay = make_overlay(width, height, stamp_rect, cert, settings)
            overlay_page = PdfReader(overlay).pages[0]
            page.merge_page(overlay_page)
        writer.add_page(page)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as stream:
        writer.write(stream)
    return output_pdf


def selected_pages(page_count: int, settings: StampSettings) -> set[int]:
    if settings.page_mode == "all":
        return set(range(page_count))
    if settings.page_mode == "first":
        return {0}
    if settings.page_mode == "last":
        return {max(0, page_count - 1)}
    return {max(0, min(page_count - 1, settings.specific_page - 1))}


def choose_stamp_rect(page, page_width: float, page_height: float, settings: StampSettings) -> Rect:
    width = settings.width_points
    height = settings.height_points
    positions = ["bottom-right", "bottom-left", "top-right", "top-left"]
    if not settings.auto_place:
        return rect_for_position(settings.position, page_width, page_height, width, height, settings)
    occupied = extract_text_rects(page)
    for position in positions:
        candidate = rect_for_position(position, page_width, page_height, width, height, settings)
        if not any(candidate.intersects(rect) for rect in occupied):
            return candidate
    return rect_for_position(settings.position, page_width, page_height, width, height, settings)


def rect_for_position(position: str, page_width: float, page_height: float, width: float, height: float, settings: StampSettings) -> Rect:
    margin = settings.margin
    if position == "bottom-left":
        x, y = margin, margin
    elif position == "top-left":
        x, y = margin, page_height - height - margin
    elif position == "top-right":
        x, y = page_width - width - margin, page_height - height - margin
    elif position == "custom":
        x, y = settings.x, settings.y
    else:
        x, y = page_width - width - margin, margin
    x = max(2, min(x, page_width - width - 2))
    y = max(2, min(y, page_height - height - 2))
    return Rect(x, y, width, height)


def extract_text_rects(page) -> list[Rect]:
    rects: list[Rect] = []

    def visitor(text, cm, tm, font_dict, font_size):
        if not text or not text.strip():
            return
        x = float(tm[4])
        y = float(tm[5])
        width = max(12.0, len(text.strip()) * float(font_size) * 0.45)
        height = max(8.0, float(font_size) * 1.2)
        rects.append(Rect(x, y, width, height))

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:
        return []
    return rects


def make_overlay(page_width: float, page_height: float, rect: Rect, cert: Certificate, settings: StampSettings) -> io.BytesIO:
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=portrait((page_width, page_height)))
    c.setFillAlpha(settings.opacity)
    c.setStrokeAlpha(settings.opacity)
    c.setStrokeColor(STAMP_BLUE)
    c.setFillColor(STAMP_BLUE)
    c.roundRect(rect.x, rect.y, rect.width, rect.height, 4, stroke=1, fill=0)

    text_left = rect.x + 8
    if settings.logo_path:
        logo_width = min(42, rect.width * 0.22) * settings.logo_scale
        draw_logo(c, rect, settings, logo_width)
        text_left += min(logo_width + 8, rect.width * 0.28)

    layout = validate_stamp_layout(settings, cert, max_width=rect.width - (text_left - rect.x) - 8)
    y = rect.top - 11
    line_height = max(layout.font_size + 1.4, layout.font_size * 1.22)
    c.setFont("Helvetica", layout.font_size)
    for line in layout.wrapped_lines:
        c.drawString(text_left, y, line[:180])
        y -= line_height
        if y < rect.y + 5:
            break

    c.save()
    packet.seek(0)
    return packet


def draw_logo(c: canvas.Canvas, rect: Rect, settings: StampSettings, size: float | None = None) -> None:
    if not settings.logo_path:
        return
    path = Path(settings.logo_path)
    if not path.exists() or path.stat().st_size > 1024 * 1024:
        return
    size = size or min(36, rect.height - 12) * settings.logo_scale
    try:
        c.drawImage(str(path), rect.x + 6, rect.top - size - 6, width=size, height=size, preserveAspectRatio=True, mask="auto")
    except Exception:
        return


def validate_stamp_layout(settings: StampSettings, cert: Certificate | None = None, *, max_width: float | None = None) -> StampLayoutResult:
    settings = settings.clone().normalize()
    errors: list[str] = []
    warnings: list[str] = []

    if settings.width_mm < 60 or settings.height_mm < 20:
        errors.append("Размер штампа не может быть меньше 60x20 мм.")
    if settings.min_font_size < 6 or settings.font_size < 6:
        errors.append("Размер шрифта не может быть меньше 6 pt.")

    inner_width = max_width if max_width is not None else settings.width_points - 12
    inner_height = settings.height_points - 10
    font_size = settings.font_size
    wrapped = wrap_stamp_lines(stamp_lines(cert or Certificate(), settings), inner_width, font_size)
    while font_size > settings.min_font_size and not text_fits(wrapped, inner_height, font_size):
        font_size -= 0.5
        wrapped = wrap_stamp_lines(stamp_lines(cert or Certificate(), settings), inner_width, font_size)

    if not text_fits(wrapped, inner_height, font_size):
        warnings.append("Текст штампа не помещается. Увеличьте размер или отключите часть полей.")
    if settings.opacity < 0.55:
        warnings.append("Прозрачность может быть слишком высокой для читаемости.")
    if settings.logo_path:
        logo = Path(settings.logo_path)
        if not logo.exists():
            warnings.append("Файл логотипа не найден.")
        elif logo.stat().st_size > 1024 * 1024:
            warnings.append("Логотип больше 1 МБ и будет проигнорирован.")

    return StampLayoutResult(font_size=font_size, wrapped_lines=wrapped, errors=errors, warnings=warnings)


def stamp_lines(cert: Certificate, settings: StampSettings, sign_time: datetime | None = None) -> list[str]:
    now = sign_time or datetime.now()
    lines = ["Документ подписан электронной подписью"]

    serial = cert.serial or "-"
    lines.append(f"Сертификат: {serial}")
    lines.append(f"Владелец: {cert.owner or '-'}")
    valid_from = _date_only(cert.not_before)
    valid_to = _date_only(cert.not_after)
    lines.append(f"Действителен: с {valid_from} по {valid_to}")

    if settings.include_signing_date_time:
        lines.append(f"Подписано: {now.strftime('%d.%m.%Y %H:%M:%S')}")
    if settings.include_organization and cert.organization:
        lines.append(f"Организация: {cert.organization}")
    if settings.include_position and cert.position:
        lines.append(f"Должность: {cert.position}")
    if settings.include_inn and cert.inn:
        lines.append(f"ИНН: {cert.inn}")
    if settings.include_snils and cert.snils:
        lines.append(f"СНИЛС: {cert.snils}")
    if settings.include_thumbprint:
        lines.append(f"Отпечаток: {format_hash(cert.thumbprint)}")
    if settings.include_issuer and cert.issuer:
        lines.append(f"Издатель: {cert.issuer}")
    if settings.include_reason and settings.reason:
        lines.append(f"Причина: {settings.reason}")
    if settings.include_date:
        template = "%d.%m.%Y %H:%M:%S" if settings.include_time else "%d.%m.%Y"
        lines.append(f"Дата: {now.strftime(template)}")
    if settings.include_custom_text and settings.custom_text:
        lines.extend(line.strip() for line in settings.custom_text.splitlines() if line.strip())
    return lines


def wrap_stamp_lines(lines: list[str], max_width: float, font_size: float, font_name: str = "Helvetica") -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        words = text.split()
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                wrapped.append(current)
                current = word
        while stringWidth(current, font_name, font_size) > max_width and len(current) > 1:
            split = max(1, int(len(current) * max_width / max(stringWidth(current, font_name, font_size), 1)))
            wrapped.append(current[:split].rstrip())
            current = current[split:].lstrip()
        wrapped.append(current)
    return wrapped


def text_fits(lines: list[str], height_points: float, font_size: float) -> bool:
    line_height = max(font_size + 1.4, font_size * 1.22)
    return len(lines) * line_height <= height_points


def format_hash(hash_value: str) -> str:
    normalized = (hash_value or "").replace(" ", "").upper()
    if len(normalized) <= 16:
        return normalized
    return normalized[:16] + "..." + normalized[-8:]


def _date_only(value: str) -> str:
    if not value:
        return "-"
    return value.split()[0]

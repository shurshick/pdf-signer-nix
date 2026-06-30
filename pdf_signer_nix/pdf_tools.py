from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import portrait
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


def stamp_pdf(input_pdf: Path, output_pdf: Path, cert: Certificate, settings: StampSettings) -> Path:
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
    width = settings.width_mm * POINTS_PER_MM
    height = settings.height_mm * POINTS_PER_MM
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
    margin = 36.0
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
    draw_logo(c, rect, settings)
    text_x = rect.x + 8
    if settings.logo_path:
        text_x += min(42, rect.width * 0.22)
    y = rect.top - 14
    c.setFont("Helvetica", 7)
    for line in stamp_lines(cert, settings):
        c.drawString(text_x, y, line[:120])
        y -= 9
        if y < rect.y + 6:
            break
    c.save()
    packet.seek(0)
    return packet


def draw_logo(c: canvas.Canvas, rect: Rect, settings: StampSettings) -> None:
    if not settings.logo_path:
        return
    path = Path(settings.logo_path)
    if not path.exists() or path.stat().st_size > 1024 * 1024:
        return
    size = min(36, rect.height - 12) * max(0.1, min(settings.logo_scale, 3.0))
    try:
        c.drawImage(str(path), rect.x + 6, rect.top - size - 6, width=size, height=size, preserveAspectRatio=True, mask="auto")
    except Exception:
        return


def stamp_lines(cert: Certificate, settings: StampSettings) -> list[str]:
    lines = ["Документ подписан электронной подписью"]
    if settings.include_owner:
        lines.append(f"Владелец: {cert.owner or '-'}")
    if settings.include_issuer:
        lines.append(f"Издатель: {cert.issuer or '-'}")
    if settings.include_serial:
        lines.append(f"Серийный номер: {cert.serial or '-'}")
    if settings.include_thumbprint:
        lines.append(f"SHA1: {cert.thumbprint or '-'}")
    if settings.include_reason:
        lines.append(f"Назначение: {settings.reason}")
    if settings.include_date:
        lines.append(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    return lines

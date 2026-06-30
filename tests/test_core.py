from __future__ import annotations

import json
from pathlib import Path

from reportlab.pdfgen import canvas

from pdf_signer_nix.crypto import parse_certmgr_output
from pdf_signer_nix.models import Certificate, StampSettings
from pdf_signer_nix.pdf_tools import Rect, rect_for_position, selected_pages, stamp_pdf
from pdf_signer_nix.settings import default_settings, import_settings, save_settings


def test_parse_certmgr_output_english():
    certs = parse_certmgr_output(
        """
1-------
Subject: CN=Ivan Ivanov, O=Org
Issuer: CN=Test CA
Serial number: 1234
SHA1 hash: aa bb cc
Container: HDIMAGE\\abc
"""
    )
    assert len(certs) == 1
    assert certs[0].owner == "Ivan Ivanov"
    assert certs[0].organization == "Org"
    assert certs[0].thumbprint == "AABBCC"


def test_rect_intersection():
    assert Rect(0, 0, 10, 10).intersects(Rect(5, 5, 10, 10))
    assert not Rect(0, 0, 10, 10).intersects(Rect(10, 0, 10, 10))


def test_selected_pages_all():
    assert selected_pages(3, StampSettings(page_mode="all")) == {0, 1, 2}


def test_selected_pages_specific_clamped():
    assert selected_pages(3, StampSettings(page_mode="specific", specific_page=99)) == {2}


def test_rect_for_bottom_right():
    settings = StampSettings(width_mm=10, height_mm=10)
    rect = rect_for_position("bottom-right", 300, 400, 100, 50, settings)
    assert rect.x == 164
    assert rect.y == 36


def test_settings_import_rejects_bad_json(tmp_path: Path):
    source = tmp_path / "bad.json"
    source.write_text("{broken", encoding="utf-8")
    try:
        import_settings(source, default_settings())
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("bad JSON accepted")


def test_settings_save(tmp_path: Path):
    target = tmp_path / "settings.json"
    save_settings(default_settings(), target)
    assert target.exists()


def test_stamp_pdf_all_pages(tmp_path: Path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "signed.pdf"
    c = canvas.Canvas(str(source))
    c.drawString(100, 700, "Page 1")
    c.showPage()
    c.drawString(100, 700, "Page 2")
    c.save()
    stamp_pdf(source, output, Certificate(subject="CN=Tester", thumbprint="ABC"), StampSettings(page_mode="all"))
    assert output.exists()
    assert output.stat().st_size > source.stat().st_size

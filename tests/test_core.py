from __future__ import annotations

import json
from pathlib import Path

from reportlab.pdfgen import canvas

from pdf_signer_nix.crypto import parse_certmgr_output
from pdf_signer_nix.diagnostics import DiagnosticItem, format_diagnostics_report
from pdf_signer_nix.models import Certificate, StampSettings
from pdf_signer_nix.pdf_tools import Rect, rect_for_position, selected_pages, stamp_lines, stamp_pdf
from pdf_signer_nix.settings import default_settings, import_settings, save_settings, stamp_from_payload
from pdf_signer_nix.update_service import parse_version


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


def test_import_windows_settings_payload(tmp_path: Path):
    source = tmp_path / "windows-settings.json"
    source.write_text(
        json.dumps(
            {
                "appVersion": "0.8.0.0",
                "settings": {
                    "VerifyAfterSigning": True,
                    "StampProfile": {
                        "Name": "ГОСТ подробный",
                        "templateName": "gost-detailed",
                        "showReason": True,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    imported = import_settings(source, default_settings())
    assert imported["verify_after_signing"] is True
    assert imported["stamp"]["template_name"] == "gost-detailed"
    assert imported["stamp"]["include_reason"] is True


def test_stamp_profile_from_windows_shape():
    stamp = stamp_from_payload(
        {
            "Name": "ГОСТ подробный",
            "templateName": "gost-detailed",
            "pageMode": "specific",
            "SpecificPage": 3,
            "positionMode": "custom",
            "customX": 77,
            "customY": 55,
            "showOrganization": True,
            "showInn": True,
            "customText": "Тест",
            "IncludeCustomText": True,
            "logoScalePercent": 150,
        }
    )
    assert stamp.template_name == "gost-detailed"
    assert stamp.page_mode == "specific"
    assert stamp.specific_page == 3
    assert stamp.position == "custom"
    assert stamp.x == 77
    assert stamp.y == 55
    assert stamp.include_organization is True
    assert stamp.include_inn is True
    assert stamp.include_custom_text is True
    assert stamp.logo_scale == 1.5


def test_stamp_lines_include_custom_fields():
    cert = Certificate(
        subject="CN=Ivan Ivanov, O=Org, T=Director, ИНН=123, СНИЛС=456",
        issuer="Test CA",
        serial="1234",
        thumbprint="11223344556677889900AABBCCDDEEFF",
    )
    stamp = StampSettings(
        template_name="custom",
        size_mode="custom",
        include_organization=True,
        include_position=True,
        include_inn=True,
        include_snils=True,
        include_issuer=True,
        include_thumbprint=True,
        include_custom_text=True,
        custom_text="Строка 1\nСтрока 2",
    )
    lines = stamp_lines(cert, stamp)
    assert any("Организация: Org" == line for line in lines)
    assert any("Должность: Director" == line for line in lines)
    assert any("ИНН: 123" == line for line in lines)
    assert any("СНИЛС: 456" == line for line in lines)
    assert any("Издатель: Test CA" == line for line in lines)
    assert any("Строка 1" == line for line in lines)


def test_parse_version_accepts_prefixed_tags():
    assert parse_version("v0.1.0") == (0, 1, 0)
    assert parse_version("1.2.3") == (1, 2, 3)


def test_format_diagnostics_report():
    report = format_diagnostics_report([DiagnosticItem("OK", "certmgr", "/opt/cprocsp/bin/amd64/certmgr")])
    assert "PDF Signer Nix diagnostics" in report
    assert "OK: certmgr:" in report


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

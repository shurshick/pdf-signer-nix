from __future__ import annotations

import json
import subprocess
from pathlib import Path

from reportlab.pdfgen import canvas

from pdf_signer_nix.crypto import ToolPaths, list_certificates, parse_certmgr_output
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


def test_parse_certmgr_output_linux_russian_sample():
    certs = parse_certmgr_output(
        """
Издатель            : ИНН ЮЛ=7707329152, E=uc@tax.gov.ru, O=Федеральная налоговая служба, CN=Федеральная налоговая служба
Субъект             : ОГРНИП=309236005500091, СНИЛС=04954357489, ИНН=232601478079, E=shurshick@bk.ru, C=RU, CN=Коваленко Александр Сергеевич, G=Александр Сергеевич, SN=Коваленко
Серийный номер      : 0x02A2174601F2B2218244CDB0E1ACB80D61
SHA1 отпечаток      : 63e689eb0b00f7b29328e77d6ef5918d04b1b381
Контейнер           : HDIMAGE\\\\356E6659.002\\CA83
Имя провайдера      : Crypto-Pro GOST R 34.10-2012 KC1 CSP
Выдан               : 04/06/2025 19:37:16 UTC
Истекает            : 04/09/2026 19:47:16 UTC
Ссылка на ключ      : Есть
Цепочка сертификатов: Успешно проверена.
#0:
  Издатель          : Минцифры России
#1:
  Субъект           : Федеральная налоговая служба
"""
    )
    assert len(certs) == 1
    cert = certs[0]
    assert cert.owner == "Коваленко Александр Сергеевич"
    assert cert.issuer.startswith("ИНН ЮЛ=7707329152")
    assert cert.serial == "0x02A2174601F2B2218244CDB0E1ACB80D61"
    assert cert.thumbprint == "63E689EB0B00F7B29328E77D6EF5918D04B1B381"
    assert cert.container == r"HDIMAGE\\356E6659.002\CA83"
    assert cert.provider == "Crypto-Pro GOST R 34.10-2012 KC1 CSP"
    assert cert.not_before == "04/06/2025 19:37:16 UTC"
    assert cert.not_after == "04/09/2026 19:47:16 UTC"
    assert cert.has_private_key is True


def test_list_certificates_parses_cp1251_stderr(monkeypatch):
    sample = """
Субъект             : CN=Коваленко Александр Сергеевич
Издатель            : CN=Федеральная налоговая служба
Серийный номер      : 0x1234
SHA1 отпечаток      : aa bb cc
""".strip()

    def fake_run_command(args: list[str], timeout: int = 120):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout=b"", stderr=sample.encode("cp1251"))

    monkeypatch.setattr("pdf_signer_nix.crypto.run_command", fake_run_command)
    certs = list_certificates(ToolPaths(certmgr=Path("/usr/bin/certmgr"), csptest=None, cryptcp=None))
    assert len(certs) == 1
    assert certs[0].owner == "Коваленко Александр Сергеевич"
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

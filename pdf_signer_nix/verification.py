from __future__ import annotations

import hashlib
import html
import tempfile
from pathlib import Path

from asn1crypto import cms as asn1cms
from pypdf import PdfReader

from . import __version__
from .crypto import verify_signature
from .models import VerificationReport


def verify_file(path: Path) -> VerificationReport:
    target = Path(path)
    report = VerificationReport(file_path=target, format=target.suffix.lstrip(".").upper())
    if not target.exists():
        report.status = "INVALID"
        report.status_description = "Файл не найден."
        report.errors.append(report.status_description)
        return report

    extension = target.suffix.lower()
    if extension == ".pdf":
        return verify_pdf(target, report)
    if extension in {".sig", ".p7s"}:
        return verify_detached(target, report)

    report.status = "INVALID"
    report.status_description = "Поддерживаются только PDF, SIG и P7S."
    report.errors.append(report.status_description)
    return report


def verify_detached(path: Path, report: VerificationReport | None = None) -> VerificationReport:
    report = report or VerificationReport(file_path=path, format=path.suffix.lstrip(".").upper())
    content = find_detached_content(path)
    if content is None:
        report.warnings.append("Рядом не найден исходный PDF. Полная detached-проверка недоступна.")

    ok, output = verify_signature(path, content)
    report.raw_output = output
    report.signature_exists = True
    report.signature_container_valid = ok
    report.pdf_readable = content is not None and is_pdf_readable(content)
    populate_report_from_cms(report, path.read_bytes())

    if ok and content is not None:
        report.status = "VALID"
        report.status_description = "Открепленная подпись корректна."
    elif ok:
        report.status = "WARNING"
        report.status_description = "Контейнер читается, но для полной проверки нужен исходный PDF."
    else:
        report.status = "INVALID"
        report.status_description = output or "Проверка открепленной подписи завершилась ошибкой."
        report.errors.append(report.status_description)
    return report


def verify_pdf(path: Path, report: VerificationReport | None = None) -> VerificationReport:
    report = report or VerificationReport(file_path=path, format="PDF")
    try:
        reader = PdfReader(str(path))
        report.pdf_readable = len(reader.pages) > 0
    except Exception as exc:
        report.status = "INVALID"
        report.status_description = str(exc)
        report.errors.append(report.status_description)
        return report

    signature = extract_pdf_signature(path, reader)
    if signature is None:
        report.status = "WARNING"
        report.status_description = "Во встроенных полях PDF подпись не найдена."
        report.warnings.append("PDF читается, но встроенной подписи не найдено.")
        return report

    report.signature_exists = True
    populate_report_from_cms(report, signature["contents"])
    with tempfile.TemporaryDirectory(prefix="pdf-signer-nix-verify-") as temp_dir:
        temp = Path(temp_dir)
        signature_path = temp / "embedded.sig"
        content_path = temp / "embedded-content.bin"
        signature_path.write_bytes(signature["contents"])
        content_path.write_bytes(signature["signed_content"])
        ok, output = verify_signature(signature_path, content_path)
        report.raw_output = output
        report.signature_container_valid = ok

    if ok:
        report.status = "VALID"
        report.status_description = "Встроенная PDF-подпись корректна."
    else:
        report.status = "INVALID"
        report.status_description = output or "Не удалось проверить встроенную PDF-подпись."
        report.errors.append(report.status_description)
    return report


def populate_report_from_cms(report: VerificationReport, cms_bytes: bytes) -> None:
    try:
        content_info = asn1cms.ContentInfo.load(cms_bytes)
    except Exception:
        return
    if content_info["content_type"].native != "signed_data":
        return

    signed_data = content_info["content"]
    signer_infos = signed_data["signer_infos"]
    if signer_infos:
        signer_info = signer_infos[0]
        digest_algorithm = signer_info["digest_algorithm"]["algorithm"].native or ""
        signature_algorithm = signer_info["signature_algorithm"]["algorithm"].native or ""
        parts = [part for part in (digest_algorithm, signature_algorithm) if part]
        if parts:
            report.certificate.signature_algorithm = " / ".join(parts)
        signed_attrs = signer_info["signed_attrs"]
        if signed_attrs is not None:
            for attr in signed_attrs:
                attr_type = attr["type"].native
                if attr_type == "signing_time":
                    values = attr["values"]
                    if values:
                        report.signing_date = str(values[0].native)
                elif attr_type == "signature_time_stamp_token":
                    report.has_timestamp = True

    certificate = find_signing_certificate(signed_data)
    if certificate is None:
        return

    report.certificate.subject = certificate.subject.human_friendly
    report.certificate.issuer = certificate.issuer.human_friendly
    report.certificate.serial_number = hex(certificate.serial_number)
    report.certificate.thumbprint = hashlib.sha1(certificate.dump()).hexdigest().upper()
    report.certificate.not_before = str(certificate["tbs_certificate"]["validity"]["not_before"].native)
    report.certificate.not_after = str(certificate["tbs_certificate"]["validity"]["not_after"].native)
    if not report.certificate.signature_algorithm:
        report.certificate.signature_algorithm = certificate["signature_algorithm"]["algorithm"].native or ""
    if not report.certificate_chain_status:
        report.certificate_chain_status = "Извлечено из CMS"


def find_signing_certificate(signed_data) -> object | None:
    signer_infos = signed_data["signer_infos"]
    certificates = signed_data["certificates"]
    if not signer_infos or not certificates:
        return None
    signer_info = signer_infos[0]
    signer_id = signer_info["sid"]
    signer_id_name = signer_id.name

    for cert_choice in certificates:
        if cert_choice.name != "certificate":
            continue
        certificate = cert_choice.chosen
        if signer_id_name == "issuer_and_serial_number":
            issuer_serial = signer_id.chosen
            if (
                certificate.serial_number == issuer_serial["serial_number"].native
                and certificate.issuer == issuer_serial["issuer"]
            ):
                return certificate
        elif signer_id_name == "subject_key_identifier":
            extensions = certificate["tbs_certificate"]["extensions"]
            if extensions is None:
                continue
            for extension in extensions:
                if extension["extn_id"].native == "key_identifier":
                    if extension["extn_value"].native == signer_id.native:
                        return certificate
    for cert_choice in certificates:
        if cert_choice.name == "certificate":
            return cert_choice.chosen
    return None


def extract_pdf_signature(path: Path, reader: PdfReader) -> dict[str, bytes] | None:
    fields = reader.trailer.get("/Root", {}).get("/AcroForm")
    if fields is None:
        return None
    field_list = fields.get_object().get("/Fields", [])
    signatures: list[dict] = []
    for field in field_list:
        collect_signature_dicts(field.get_object(), signatures)
    if not signatures:
        return None

    signature = signatures[-1]
    contents = signature.get("/Contents")
    byte_range = signature.get("/ByteRange")
    if contents is None or byte_range is None or len(byte_range) < 4:
        return None

    if hasattr(contents, "original_bytes"):
        signature_bytes = bytes(contents.original_bytes)
    else:
        signature_bytes = bytes(contents)
    signature_bytes = signature_bytes.rstrip(b"\x00")

    file_bytes = path.read_bytes()
    signed_parts = bytearray()
    numbers = [int(value) for value in byte_range]
    for index in range(0, len(numbers), 2):
        offset = numbers[index]
        length = numbers[index + 1]
        signed_parts.extend(file_bytes[offset : offset + length])

    return {"contents": signature_bytes, "signed_content": bytes(signed_parts)}


def collect_signature_dicts(field, signatures: list[dict]) -> None:
    if field.get("/FT") == "/Sig" and field.get("/V") is not None:
        signatures.append(field["/V"].get_object())
    for kid in field.get("/Kids", []) or []:
        collect_signature_dicts(kid.get_object(), signatures)


def find_detached_content(signature_path: Path) -> Path | None:
    exact = signature_path.with_suffix(".pdf")
    if exact.exists():
        return exact
    stem = signature_path.stem
    if stem.endswith("-signed"):
        candidate = signature_path.with_name(stem[: -len("-signed")] + ".pdf")
        if candidate.exists():
            return candidate
    return None


def is_pdf_readable(path: Path) -> bool:
    try:
        reader = PdfReader(str(path))
        return len(reader.pages) > 0
    except Exception:
        return False


def report_to_text(report: VerificationReport) -> str:
    lines = [
        "PDF Signer Nix verification report",
        f"Application version: {__version__}",
        f"File: {report.file_path}",
        f"Format: {report.format or '-'}",
        "",
        f"Status: {report.status}",
        f"Description: {report.status_description}",
        f"Signature exists: {'yes' if report.signature_exists else 'no'}",
        f"Signature container valid: {'yes' if report.signature_container_valid else 'no'}",
        f"PDF readable: {'yes' if report.pdf_readable else 'no'}",
        f"Certificate chain: {report.certificate_chain_status or '-'}",
        "",
        "Certificate",
        f"Subject: {report.certificate.subject or '-'}",
        f"Issuer: {report.certificate.issuer or '-'}",
        f"Serial number: {report.certificate.serial_number or '-'}",
        f"Thumbprint: {report.certificate.thumbprint or '-'}",
        f"Signature algorithm: {report.certificate.signature_algorithm or '-'}",
        f"Valid from: {report.certificate.not_before or '-'}",
        f"Valid to: {report.certificate.not_after or '-'}",
        "",
        "Warnings",
    ]
    if report.warnings:
        lines.extend(f"- {item}" for item in report.warnings)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Errors")
    if report.errors:
        lines.extend(f"- {item}" for item in report.errors)
    else:
        lines.append("- none")
    if report.raw_output:
        lines.extend(["", "Raw output", report.raw_output])
    return "\n".join(lines)


def report_to_html(report: VerificationReport) -> str:
    def row(name: str, value: str, raw: bool = False) -> str:
        cell = value if raw else html.escape(value or "-")
        return f"<tr><th>{html.escape(name)}</th><td>{cell}</td></tr>"

    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in report.warnings) or "<li>none</li>"
    errors = "".join(f"<li>{html.escape(item)}</li>" for item in report.errors) or "<li>none</li>"
    raw_output = f"<h2>Raw output</h2><pre>{html.escape(report.raw_output)}</pre>" if report.raw_output else ""
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>Verification report</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#1f2937}"
        "table{border-collapse:collapse;width:100%;margin:12px 0}"
        "td,th{border:1px solid #d1d5db;padding:6px 8px;text-align:left}"
        ".status{font-weight:700}.VALID{color:#0f7b35}.WARNING{color:#a15c00}.INVALID{color:#b42318}</style>"
        "</head><body>"
        "<h1>PDF Signer Nix verification report</h1>"
        "<table>"
        + row("File", str(report.file_path))
        + row("Format", report.format)
        + row("Status", f"<span class=\"status {report.status}\">{report.status}</span>", True)
        + row("Description", report.status_description)
        + row("Signature exists", "yes" if report.signature_exists else "no")
        + row("Signature container valid", "yes" if report.signature_container_valid else "no")
        + row("PDF readable", "yes" if report.pdf_readable else "no")
        + row("Certificate chain", report.certificate_chain_status or "-")
        + "</table><h2>Certificate</h2><table>"
        + row("Subject", report.certificate.subject)
        + row("Issuer", report.certificate.issuer)
        + row("Serial number", report.certificate.serial_number)
        + row("Thumbprint", report.certificate.thumbprint)
        + row("Signature algorithm", report.certificate.signature_algorithm)
        + row("Valid from", report.certificate.not_before)
        + row("Valid to", report.certificate.not_after)
        + f"</table><h2>Warnings</h2><ul>{warnings}</ul><h2>Errors</h2><ul>{errors}</ul>{raw_output}</body></html>"
    )

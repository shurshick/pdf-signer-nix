from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import Certificate


CPRO_BIN_DIRS = (
    Path("/opt/cprocsp/bin/amd64"),
    Path("/opt/cprocsp/bin"),
    Path("/opt/cprocsp/sbin/amd64"),
)


@dataclass(slots=True)
class ToolPaths:
    certmgr: Path | None
    csptest: Path | None
    cryptcp: Path | None

    @property
    def has_crypto_pro(self) -> bool:
        return self.certmgr is not None and (self.csptest is not None or self.cryptcp is not None)


class CryptoProError(RuntimeError):
    pass


def find_tool(name: str) -> Path | None:
    env_name = f"PDF_SIGNER_NIX_{name.upper()}"
    if os.environ.get(env_name):
        candidate = Path(os.environ[env_name])
        if candidate.exists():
            return candidate
    path = shutil.which(name)
    if path and is_crypto_tool_path(Path(path)):
        return Path(path)
    for directory in CPRO_BIN_DIRS:
        candidate = directory / name
        if candidate.exists():
            return candidate
    return None


def is_crypto_tool_path(path: Path) -> bool:
    if path.suffix.lower() in {".msc", ".lnk"}:
        return False
    return True


def discover_tools() -> ToolPaths:
    return ToolPaths(certmgr=find_tool("certmgr"), csptest=find_tool("csptest"), cryptcp=find_tool("cryptcp"))


def run_command(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, text=False, capture_output=True, timeout=timeout, check=False)


def decode_tool_output(data: bytes | str | None) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    for encoding in ("utf-8", "cp1251", "cp866"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def tool_output(proc: subprocess.CompletedProcess[bytes]) -> str:
    parts = [decode_tool_output(part).strip() for part in (proc.stdout, proc.stderr) if part]
    return "\n".join(part for part in parts if part)


def list_certificates(tools: ToolPaths | None = None) -> list[Certificate]:
    tools = tools or discover_tools()
    if tools.certmgr is None:
        raise CryptoProError("certmgr не найден. Установите CryptoPro CSP или задайте PDF_SIGNER_NIX_CERTMGR.")

    certificates: list[Certificate] = []
    errors: list[str] = []
    for store in ("uMy", "mMy"):
        proc = run_command([str(tools.certmgr), "-list", "-store", store])
        output = tool_output(proc)
        parsed = parse_certmgr_output(output)
        if parsed:
            certificates.extend(parsed)
            continue
        if proc.returncode != 0:
            errors.append(f"{store}: {output or 'certmgr failed'}")

    if certificates:
        return dedupe_certificates(certificates)
    if errors:
        raise CryptoProError("\n".join(errors))
    return []


def dedupe_certificates(certificates: list[Certificate]) -> list[Certificate]:
    unique: list[Certificate] = []
    seen: set[tuple[str, str, str]] = set()
    for cert in certificates:
        key = (
            cert.thumbprint.upper(),
            cert.serial.upper(),
            cert.subject.strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(cert)
    return unique


def parse_certmgr_output(text: str) -> list[Certificate]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^\d+-{4,}$", line) and current:
            blocks.append(current)
            current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)

    certificates = [parse_cert_block(block) for block in blocks]
    return [cert for cert in certificates if cert.subject or cert.thumbprint or cert.serial]


def parse_cert_block(lines: list[str]) -> Certificate:
    cert = Certificate()
    for line in lines:
        if line.startswith("#"):
            continue
        key, value = split_field(line)
        normalized = normalize_field_name(key)
        if normalized.startswith(("certificate chain", "цепочка сертификатов")):
            break
        if normalized.startswith(("subject", "субъект")) and not cert.subject:
            cert.subject = value
        elif normalized.startswith(("issuer", "издатель")) and not cert.issuer:
            cert.issuer = value
        elif normalized.startswith(("serial number", "серийный номер")) and not cert.serial:
            cert.serial = value.replace(" ", "")
        elif ("sha1" in normalized or "отпечат" in normalized) and not cert.thumbprint:
            cert.thumbprint = value.replace(" ", "").upper()
        elif normalized.startswith(("container", "контейнер")) and not cert.container:
            cert.container = value
        elif normalized.startswith(("provider name", "имя провайдера")) and not cert.provider:
            cert.provider = value
        elif normalized.startswith(("not valid before", "notbefore", "действителен с", "выдан")) and not cert.not_before:
            cert.not_before = value
        elif normalized.startswith(("not valid after", "notafter", "действителен до", "истекает")) and not cert.not_after:
            cert.not_after = value
        elif normalized.startswith(("private key link", "private key", "ссылка на ключ")):
            lowered = value.lower()
            cert.has_private_key = lowered not in {"", "нет", "no", "not found", "absent"}
    return cert


def normalize_field_name(key: str) -> str:
    return " ".join(key.strip().lower().replace("ё", "е").split())


def split_field(line: str) -> tuple[str, str]:
    if ":" not in line:
        return line.strip(), ""
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def sign_detached(input_path: Path, output_sig: Path, cert: Certificate, tools: ToolPaths | None = None) -> Path:
    tools = tools or discover_tools()
    if tools.csptest is None:
        raise CryptoProError("csptest не найден. Невозможно создать открепленную подпись .sig.")
    selector = cert.thumbprint or cert.owner
    if not selector:
        raise CryptoProError("Не выбран сертификат подписи.")
    output_sig.parent.mkdir(parents=True, exist_ok=True)
    args = [
        str(tools.csptest),
        "-sfsign",
        "-sign",
        "-detached",
        "-add",
        "-my",
        selector,
        "-in",
        str(input_path),
        "-out",
        str(output_sig),
    ]
    proc = run_command(args, timeout=240)
    if proc.returncode != 0 or not output_sig.exists():
        raise CryptoProError(format_tool_error("Ошибка создания .sig", proc))
    return output_sig


def sign_embedded_pdf(input_pdf: Path, output_pdf: Path, cert: Certificate, tools: ToolPaths | None = None) -> Path:
    tools = tools or discover_tools()
    if tools.cryptcp is None:
        raise CryptoProError(
            "cryptcp не найден. Для встроенной PDF-подписи требуется CryptoPro cryptcp. "
            "Можно создать открепленную .sig подпись."
        )
    selector = cert.thumbprint or cert.owner
    if not selector:
        raise CryptoProError("Не выбран сертификат подписи.")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    args = [
        str(tools.cryptcp),
        "-signf",
        "-cert",
        "-der",
        "-strict",
        "-thumbprint",
        selector,
        "-attached",
        "-nochain",
        "-out",
        str(output_pdf),
        str(input_pdf),
    ]
    proc = run_command(args, timeout=240)
    if proc.returncode != 0 or not output_pdf.exists():
        raise CryptoProError(format_tool_error("Ошибка встроенной PDF-подписи", proc))
    return output_pdf


def verify_signature(target: Path, content: Path | None = None, tools: ToolPaths | None = None) -> tuple[bool, str]:
    tools = tools or discover_tools()
    if tools.csptest is None:
        return False, "csptest не найден."
    args = [str(tools.csptest), "-sfsign", "-verify", "-in", str(target)]
    if content is not None:
        args.extend(["-content", str(content)])
    proc = run_command(args, timeout=120)
    ok = proc.returncode == 0
    return ok, tool_output(proc)


def format_tool_error(prefix: str, proc: subprocess.CompletedProcess[bytes]) -> str:
    body = tool_output(proc)
    if body:
        return f"{prefix}: {body}"
    return f"{prefix}: код возврата {proc.returncode}"

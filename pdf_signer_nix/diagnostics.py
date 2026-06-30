from __future__ import annotations

from dataclasses import asdict, dataclass

from .crypto import CryptoProError, discover_tools, list_certificates
from .paths import log_dir
from .update_service import get_current_version_text


@dataclass(slots=True)
class DiagnosticItem:
    status: str
    title: str
    message: str


def run_diagnostics() -> list[DiagnosticItem]:
    tools = discover_tools()
    items: list[DiagnosticItem] = []
    items.append(tool_item("certmgr", tools.certmgr))
    items.append(tool_item("csptest", tools.csptest))
    items.append(tool_item("cryptcp", tools.cryptcp, warning_if_missing=True))
    try:
        certs = list_certificates(tools)
        if certs:
            items.append(DiagnosticItem("OK", "Сертификаты", f"Найдено сертификатов: {len(certs)}"))
        else:
            items.append(DiagnosticItem("WARNING", "Сертификаты", "Сертификаты в хранилищах uMy и mMy не найдены."))
    except CryptoProError as exc:
        items.append(DiagnosticItem("ERROR", "Сертификаты", str(exc)))
    return items


def diagnostics_json() -> list[dict]:
    return [asdict(item) for item in run_diagnostics()]


def format_diagnostics_report(items: list[DiagnosticItem] | None = None) -> str:
    rows = items or run_diagnostics()
    lines = [
        "PDF Signer Nix diagnostics",
        f"Version: {get_current_version_text()}",
        f"Logs: {log_dir() / 'app.log'}",
        "",
    ]
    for item in rows:
        lines.append(f"{item.status}: {item.title}: {item.message}")
    return "\n".join(lines)


def tool_item(name: str, path, warning_if_missing: bool = False) -> DiagnosticItem:
    if path:
        return DiagnosticItem("OK", name, str(path))
    return DiagnosticItem("WARNING" if warning_if_missing else "ERROR", name, f"{name} не найден.")

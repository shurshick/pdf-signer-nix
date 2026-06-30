from __future__ import annotations

import argparse
import logging

from . import __version__
from .diagnostics import run_diagnostics
from .logging_setup import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdf-signer-nix")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--self-test", action="store_true", help="run non-CryptoPro startup checks")
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0
    configure_logging()
    logging.info("PDF Signer Nix %s started", __version__)
    if args.self_test:
        for item in run_diagnostics():
            print(f"{item.status}: {item.title}: {item.message}")
        return 0

    from .gui import run_gui

    return run_gui()

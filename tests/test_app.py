from __future__ import annotations

from pdf_signer_nix.app import main


def test_version(capsys):
    assert main(["--version"]) == 0
    assert "0.2.8" in capsys.readouterr().out


def test_self_test_without_cryptopro():
    assert main(["--self-test"]) == 0

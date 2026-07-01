#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
cd "${ROOT_DIR}"

if [[ "${SKIP_BINARY_BUILD:-0}" == "1" ]]; then
  test -x artifacts/pdf-signer-nix
  artifacts/pdf-signer-nix --version
  exit 0
fi

${PYTHON_BIN} -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[dev]'
pyinstaller \
  --clean \
  --onefile \
  --name pdf-signer-nix \
  --add-data "assets/pdf-signer-nix.png:assets" \
  --add-data "assets/DejaVuSans.ttf:assets" \
  launcher.py

mkdir -p artifacts
cp -f dist/pdf-signer-nix artifacts/pdf-signer-nix
artifacts/pdf-signer-nix --version

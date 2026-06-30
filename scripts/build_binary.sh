#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python3 -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[dev]'
pyinstaller \
  --clean \
  --onefile \
  --name pdf-signer-nix \
  launcher.py

mkdir -p artifacts
cp -f dist/pdf-signer-nix artifacts/pdf-signer-nix
artifacts/pdf-signer-nix --version

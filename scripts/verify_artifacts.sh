#!/usr/bin/env bash
set -euo pipefail

VERSION="${VERSION:-0.1.0}"
ARTIFACTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/artifacts"

test -x "${ARTIFACTS}/pdf-signer-nix"
test -f "${ARTIFACTS}/pdf-signer-nix_${VERSION}_amd64.deb"
test -n "$(find "${ARTIFACTS}" -maxdepth 1 -name 'pdf-signer-nix-*.rpm' -print -quit)"
"${ARTIFACTS}/pdf-signer-nix" --version | grep -q "${VERSION}"
dpkg-deb -c "${ARTIFACTS}/pdf-signer-nix_${VERSION}_amd64.deb" | grep -q '/usr/bin/pdf-signer-nix'
sha256sum "${ARTIFACTS}"/* > "${ARTIFACTS}/SHA256SUMS.txt"
cat "${ARTIFACTS}/SHA256SUMS.txt"

#!/usr/bin/env bash
set -euo pipefail

VERSION="${VERSION:-0.2.1}"
ARTIFACTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/artifacts"

test -x "${ARTIFACTS}/pdf-signer-nix"
test -f "${ARTIFACTS}/pdf-signer-nix_${VERSION}_amd64.deb"
test -n "$(find "${ARTIFACTS}" -maxdepth 1 -name 'pdf-signer-nix-*.rpm' -print -quit)"
"${ARTIFACTS}/pdf-signer-nix" --version | grep -q "${VERSION}"
dpkg-deb -c "${ARTIFACTS}/pdf-signer-nix_${VERSION}_amd64.deb" > "${ARTIFACTS}/deb-contents.txt"
grep -q '/usr/bin/pdf-signer-nix' "${ARTIFACTS}/deb-contents.txt"
rm -f "${ARTIFACTS}/deb-contents.txt"
(cd "${ARTIFACTS}" && sha256sum pdf-signer-nix *.deb *.rpm > SHA256SUMS.txt)
cat "${ARTIFACTS}/SHA256SUMS.txt"

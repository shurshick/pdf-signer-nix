#!/usr/bin/env bash
set -euo pipefail

VERSION="${VERSION:-0.2.3}"
ARCH="${DEB_ARCH:-amd64}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILDROOT="$(mktemp -d)"
ARTIFACTS="${ROOT_DIR}/artifacts"
trap 'rm -rf "${BUILDROOT}"' EXIT

"${ROOT_DIR}/scripts/build_binary.sh"
mkdir -p \
  "${BUILDROOT}/DEBIAN" \
  "${BUILDROOT}/usr/bin" \
  "${BUILDROOT}/usr/share/applications" \
  "${BUILDROOT}/usr/share/icons/hicolor/512x512/apps" \
  "${BUILDROOT}/usr/share/doc/pdf-signer-nix"

install -m 0755 "${ARTIFACTS}/pdf-signer-nix" "${BUILDROOT}/usr/bin/pdf-signer-nix"
install -m 0644 "${ROOT_DIR}/packaging/pdf-signer-nix.desktop" "${BUILDROOT}/usr/share/applications/pdf-signer-nix.desktop"
install -m 0644 "${ROOT_DIR}/assets/pdf-signer-nix.png" "${BUILDROOT}/usr/share/icons/hicolor/512x512/apps/pdf-signer-nix.png"
install -m 0644 "${ROOT_DIR}/README.md" "${BUILDROOT}/usr/share/doc/pdf-signer-nix/README.md"

cat > "${BUILDROOT}/DEBIAN/control" <<EOF
Package: pdf-signer-nix
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: shurshick <noreply@example.com>
Homepage: https://github.com/shurshick/pdf-signer-nix
Depends: libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libx11-xcb1, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-icccm4, libatomic1, fontconfig
Description: PDF signing and visible stamp tool for Linux with CryptoPro CSP
 PDF Signer Nix is a local desktop application for signing PDF files
 through CryptoPro CSP tools and adding a visible signature stamp.
 CryptoPro CSP is required at runtime and is not bundled.
EOF

dpkg-deb --build --root-owner-group "${BUILDROOT}" "${ARTIFACTS}/pdf-signer-nix_${VERSION}_${ARCH}.deb"

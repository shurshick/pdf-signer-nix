#!/usr/bin/env bash
set -euo pipefail

VERSION="${VERSION:-0.2.1}"
RELEASE="${RELEASE:-1}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RPMROOT="$(mktemp -d)"
ARTIFACTS="${ROOT_DIR}/artifacts"
trap 'rm -rf "${RPMROOT}"' EXIT

"${ROOT_DIR}/scripts/build_binary.sh"
mkdir -p "${RPMROOT}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -f "${ARTIFACTS}/pdf-signer-nix" "${RPMROOT}/SOURCES/"
cp -f "${ROOT_DIR}/packaging/pdf-signer-nix.desktop" "${RPMROOT}/SOURCES/"
cp -f "${ROOT_DIR}/assets/pdf-signer-nix.png" "${RPMROOT}/SOURCES/"
cp -f "${ROOT_DIR}/README.md" "${RPMROOT}/SOURCES/"

cat > "${RPMROOT}/SPECS/pdf-signer-nix.spec" <<EOF
Name:           pdf-signer-nix
Version:        ${VERSION}
Release:        ${RELEASE}%{?dist}
Summary:        PDF signing and visible stamp tool for Linux with CryptoPro CSP
License:        AGPL-3.0-or-later
URL:            https://github.com/shurshick/pdf-signer-nix
BuildArch:      x86_64
Requires:       mesa-libEGL
Requires:       libxkbcommon
Requires:       fontconfig

%description
PDF Signer Nix is a local desktop application for signing PDF files
through CryptoPro CSP tools and adding a visible signature stamp.

%prep

%build

%install
install -D -m 0755 %{_sourcedir}/pdf-signer-nix %{buildroot}/usr/bin/pdf-signer-nix
install -D -m 0644 %{_sourcedir}/pdf-signer-nix.desktop %{buildroot}/usr/share/applications/pdf-signer-nix.desktop
install -D -m 0644 %{_sourcedir}/pdf-signer-nix.png %{buildroot}/usr/share/icons/hicolor/512x512/apps/pdf-signer-nix.png
install -D -m 0644 %{_sourcedir}/README.md %{buildroot}/usr/share/doc/pdf-signer-nix/README.md

%files
/usr/bin/pdf-signer-nix
/usr/share/applications/pdf-signer-nix.desktop
/usr/share/icons/hicolor/512x512/apps/pdf-signer-nix.png
/usr/share/doc/pdf-signer-nix/README.md

%changelog
* Tue Jun 30 2026 shurshick <noreply@example.com> ${VERSION}-${RELEASE}
- Initial pdf-signer-nix release.
EOF

rpmbuild -bb "${RPMROOT}/SPECS/pdf-signer-nix.spec" --define "_topdir ${RPMROOT}"
find "${RPMROOT}/RPMS" -type f -name '*.rpm' -exec cp -f {} "${ARTIFACTS}/" \;

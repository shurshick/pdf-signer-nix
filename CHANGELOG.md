# Changelog

## v0.2.2

- Rebuilt Linux artifacts on an EL8-compatible base to restore runtime compatibility with RedOS 8 and other glibc 2.28 systems.
- Pinned PySide6 to the EL8-compatible 6.8 branch and made the build scripts accept a custom Python binary.

## v0.2.1

- Fixed RPM packaging so the app no longer hard-requires CryptoPro binaries at install time.
- Added Linux GUI runtime dependencies to DEB/RPM packages so the installed app starts on clean systems.
- Switched the application icon to the Windows project icon with a transparent PNG background.

## v0.2.0

- Added a full stamp editor with built-in GOST profiles, custom profile save/load, manual coordinates, preview drag, logo scaling, and stamp field toggles.
- Added signature verification dialog for PDF, `.sig`, and `.p7s` with TXT/HTML export and copyable reports.
- Added diagnostics dialog with report export and direct access to the logs folder.
- Added About dialog with GitHub release update checks.
- Added settings/profile compatibility with exported JSON from the Windows version.
- Expanded tests and re-verified Linux packaging, checksums, DEB install, RPM metadata, and standalone binary smoke under WSL.

## v0.1.0

- Initial Python implementation from scratch.
- Added native Python/Qt desktop UI.
- Added CryptoPro tool discovery and diagnostics.
- Added certificate parsing through `certmgr`.
- Added visible PDF stamp with pypdf/reportlab.
- Added smart stamp placement based on text rectangles.
- Added detached `.sig` signing through `csptest`.
- Added embedded PDF signing path through `cryptcp`.
- Added settings export/import.
- Added DEB/RPM packaging and GitHub Actions release artifacts.

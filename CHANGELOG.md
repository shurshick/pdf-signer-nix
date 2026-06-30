# Changelog

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

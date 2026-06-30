# Release Notes

## v0.2.4

Patch release with CryptoPro output handling fix.

### Русский

- Исправлен разбор сертификатов на Linux: теперь приложение читает вывод `certmgr` и из `stdout`, и из `stderr`.

### English

- Fixed certificate parsing on Linux: the app now reads `certmgr` output from both `stdout` and `stderr`.

## v0.2.3

Patch release with CryptoPro certificate store fix.

### Русский

- Исправлен поиск сертификатов: приложение теперь читает хранилища `uMy` и `mMy`, а не только `uMy`.

### English

- Fixed certificate discovery: the app now reads both `uMy` and `mMy` CryptoPro stores instead of only `uMy`.

## v0.2.2

Patch release with EL8 compatibility fixes.

### Русский

- Linux-артефакты пересобраны на EL8-совместимой базе, чтобы RPM запускался на RedOS 8 и других системах с glibc 2.28.
- `PySide6` зафиксирован на ветке `6.8.x`, совместимой с EL8.
- Сборочные скрипты теперь принимают `PYTHON_BIN`, чтобы релиз можно было собирать на системном `python3.12` в AlmaLinux 8.

### English

- Rebuilt Linux artifacts on an EL8-compatible base so the RPM starts on RedOS 8 and other glibc 2.28 systems.
- Pinned `PySide6` to the EL8-compatible `6.8.x` branch.
- Build scripts now accept `PYTHON_BIN` so releases can be built with the system `python3.12` on AlmaLinux 8.

## v0.2.1

Patch release with packaging fixes.

### Русский

- Исправлена RPM-упаковка: пакет больше не требует бинарники CryptoPro на этапе установки.
- В DEB и RPM добавлены системные зависимости для Qt/EGL, чтобы установленное приложение запускалось на чистой системе.
- В проект и пакеты добавлена нормальная PNG-иконка из Windows-версии с прозрачным фоном.

### English

- Fixed RPM packaging so the package no longer requires CryptoPro binaries during installation.
- Added Qt/EGL runtime dependencies to DEB and RPM packages so the installed app starts on clean systems.
- Replaced the project icon with the Windows version PNG icon with a transparent background.

## v0.2.0

Linux-версия `pdf-signer-nix` стала нормальным desktop-портом по ключевым пользовательским сценариям Windows-версии.

### Русский

- Добавлен полноценный редактор штампа с профилями `ГОСТ минимальный`, `ГОСТ стандартный`, `ГОСТ подробный` и `Custom`.
- Добавлены ручные координаты X/Y, drag штампа по preview, сброс позиции, логотип и свой текст.
- Добавлено отдельное окно проверки подписи для PDF, `.sig`, `.p7s` с копированием и экспортом TXT/HTML-отчётов.
- Добавлено отдельное окно диагностики с сохранением отчёта и переходом к логам.
- Добавлено окно `О приложении` с проверкой новых релизов на GitHub.
- Добавлен совместимый import/export JSON настроек и профилей с Windows-версией.
- Перепроверены Linux-артефакты: standalone binary, `.deb`, `.rpm`, `SHA256SUMS`.

### English

- Added a full stamp editor with built-in `GOST minimal`, `GOST standard`, `GOST detailed`, and `Custom` profiles.
- Added manual X/Y coordinates, preview drag, reset position, logo support, and custom text.
- Added a dedicated signature verification window for PDF, `.sig`, and `.p7s` with copyable TXT/HTML reports.
- Added a dedicated diagnostics window with report export and direct access to logs.
- Added an About dialog with GitHub release update checks.
- Added JSON settings/profile compatibility with exports from the Windows version.
- Re-verified Linux artifacts: standalone binary, `.deb`, `.rpm`, and `SHA256SUMS`.

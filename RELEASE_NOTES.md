# Release Notes

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

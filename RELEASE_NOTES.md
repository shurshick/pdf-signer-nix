# PDF Signer Nix v0.2.8

Исправлен основной рабочий сценарий подписи на Linux.

## Что исправлено

- Встроенная PDF-подпись больше не ломается на `cryptcp: unrecognized option '-out'`.
- Подпись теперь встраивается в PDF корректно: приложение резервирует `ByteRange` в документе, получает detached CMS-подпись от `csptest` и записывает её обратно в PDF.
- Видимый штамп больше не рисует квадраты вместо кириллицы: в приложение добавлен `DejaVuSans.ttf`, который пакуется и в portable-бинарник.
- Тесты и сборка обновлены под новый путь подписи и новый ассет шрифта.

## English

Fixed the main Linux signing flow.

- Embedded PDF signing no longer fails with `cryptcp: unrecognized option '-out'`.
- The app now reserves a PDF `ByteRange`, creates a detached CMS signature with `csptest`, and embeds that CMS back into the PDF.
- The visible stamp now uses a bundled `DejaVuSans.ttf`, so Cyrillic text no longer renders as squares.

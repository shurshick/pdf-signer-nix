# PDF Signer Nix v0.2.10

Исправлена логика выходных файлов и превью штампа.

## Что исправлено

- Теперь всегда создаётся один итоговый PDF `*-signed.pdf`.
- Лишний промежуточный файл `*-signed-embedded.pdf` больше не остаётся рядом с результатом.
- Detached-режим работает как отдельный режим: итоговый PDF со штампом плюс `.sig`, без лишней встроенной подписи.
- Исправлена рамка в предпросмотре редактора штампа.

## English

Fixed output file logic and the stamp preview.

- The app now always writes a single final `*-signed.pdf`.
- The stray intermediate `*-signed-embedded.pdf` file is gone.
- Detached mode now behaves as a real separate mode: stamped PDF plus `.sig`, without an extra embedded-signature attempt.
- Fixed the stamp editor preview frame rendering.

# PDF Signer Nix v0.2.11

Исправлена подготовка встроенной PDF-подписи для внешних валидаторов.

## Что исправлено

- Перед записью в `/Contents` встроенная CMS-подпись теперь нормализуется. Это убирает расхождения между detached-проверкой CryptoPro и проверкой встроенной PDF-подписи внешними средствами.
- Логика режимов подписи из `v0.2.10` сохранена: встроенный режим создаёт один итоговый PDF, detached-режим создаёт `*-signed.pdf` и `.sig`.

## English

Normalized the embedded CMS signature before writing it into the PDF signature container.

- This targets compatibility with stricter third-party PDF validators that accepted the detached signature but rejected the embedded PDF signature container.
- The `v0.2.10` signing mode cleanup remains in place.

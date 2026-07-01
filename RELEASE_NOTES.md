# PDF Signer Nix v0.2.6

Исправлен ещё один реальный сбой поиска сертификатов на Linux.

## Что исправлено

- Разбор сертификатов теперь не зависит только от точного текста заголовков `certmgr`.
- Добавлен запасной разбор по типу значения и порядку строк: DN, серийный номер, SHA1, контейнер, провайдер, даты, признак ключа.
- За счёт этого приложение корректно подхватывает сертификат из реального вывода `certmgr -list -store uMy`, который раньше в `0.2.5` всё ещё не попадал в список.

## English

Another real Linux certificate-discovery failure has been fixed.

- Certificate parsing no longer depends only on exact `certmgr` field labels.
- Added fallback parsing by value type and line order: DN, serial, SHA1, container, provider, dates, and private-key marker.
- This fixes the real `certmgr -list -store uMy` output that still failed in `0.2.5`.

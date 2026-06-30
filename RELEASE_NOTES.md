# PDF Signer Nix v0.2.4

Небольшой, но важный релиз.

## Что исправлено

- Исправлен разбор вывода `certmgr` на Linux.
- Приложение теперь читает список сертификатов и из `stdout`, и из `stderr`.

## Зачем это нужно

На части Linux-систем CryptoPro печатает список сертификатов не в `stdout`, а в `stderr`. Из-за этого сертификаты реально были в системе, но приложение их не видело.

## English

Small but important fix release.

- Fixed Linux certificate parsing for `certmgr`.
- The app now reads certificate listings from both `stdout` and `stderr`.

# CryptoPro

`pdf-signer-nix` работает поверх установленного CryptoPro CSP и вызывает его штатные утилиты.

## Что используется

- `certmgr` - список сертификатов;
- `csptest` - открепленная подпись `.sig` и часть проверок;
- `cryptcp` - встроенная подпись PDF, если доступен в системе.

## Где приложение их ищет

Обычные пути:

- `/usr/bin/certmgr`
- `/opt/cprocsp/bin/amd64/certmgr`
- `/opt/cprocsp/bin/amd64/csptest`
- `/opt/cprocsp/bin/amd64/cryptcp`

Пути можно переопределить переменными окружения:

```bash
PDF_SIGNER_NIX_CERTMGR=/path/to/certmgr
PDF_SIGNER_NIX_CSPTEST=/path/to/csptest
PDF_SIGNER_NIX_CRYPTCP=/path/to/cryptcp
```

## Как ищутся сертификаты

Приложение читает оба хранилища CryptoPro:

- `uMy`
- `mMy`

Именно так и должно быть. Искать только в `uMy` было ошибкой.

На Linux `certmgr` может печатать список сертификатов в `stdout` или в `stderr`. `pdf-signer-nix` учитывает оба варианта.

## Быстрая проверка

```bash
pdf-signer-nix --self-test
certmgr -list -store uMy
certmgr -list -store mMy
```

Если приложение не видит сертификат, а `certmgr` его показывает, это уже повод смотреть лог:

```text
~/.local/share/PDF Signer Nix/logs/app.log
```

## Ограничение

CryptoPro в релиз не входит и должен быть установлен отдельно.

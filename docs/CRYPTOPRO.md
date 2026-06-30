# CryptoPro

Приложение использует инструменты CryptoPro CSP:

- `certmgr` для списка сертификатов;
- `csptest` для открепленной `.sig` подписи и проверки;
- `cryptcp` для встроенной PDF-подписи, если он доступен.

Пути можно переопределить переменными:

```bash
PDF_SIGNER_NIX_CERTMGR=/path/to/certmgr
PDF_SIGNER_NIX_CSPTEST=/path/to/csptest
PDF_SIGNER_NIX_CRYPTCP=/path/to/cryptcp
```

CryptoPro не входит в пакет и должен быть установлен пользователем отдельно.

# Packaging

Проект публикует четыре артефакта:

- `pdf-signer-nix` - standalone binary;
- `pdf-signer-nix_*.deb`;
- `pdf-signer-nix-*.rpm`;
- `SHA256SUMS.txt`.

## Как собирается релиз

- тесты гоняются на `ubuntu-24.04`;
- standalone binary и RPM собираются в `AlmaLinux 8`;
- DEB собирается на Ubuntu из уже готового EL8-бинарника;
- после этого проверяются checksums, установка DEB и smoke-запуск GUI.

Такой пайплайн нужен не для красоты, а для совместимости. Сборка на новой Ubuntu ломала запуск RPM на RedOS 8 из-за слишком новой `glibc`.

## Что кладется в пакеты

- `/usr/bin/pdf-signer-nix`
- `/usr/share/applications/pdf-signer-nix.desktop`
- `/usr/share/icons/hicolor/512x512/apps/pdf-signer-nix.png`
- `/usr/share/doc/pdf-signer-nix/README.md`

## Что не кладется

CryptoPro CSP не бандлится. Это внешняя зависимость, которая должна уже стоять в системе пользователя.

## Проверки

Минимальный набор локальных проверок перед релизом:

```bash
pytest -q
VERSION=0.2.5 ./scripts/build_deb.sh
VERSION=0.2.5 ./scripts/build_rpm.sh
VERSION=0.2.5 ./scripts/verify_artifacts.sh
```

Для RPM одной сборки мало. Нужен запуск на целевой системе или в совместимом окружении вроде RedOS 8, AlmaLinux 8, Rocky 8.

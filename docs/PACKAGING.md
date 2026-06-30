# Packaging

Сборка релиза выполняется на Ubuntu в GitHub Actions.

Пакеты содержат:

- `/usr/bin/pdf-signer-nix`;
- `/usr/share/applications/pdf-signer-nix.desktop`;
- `/usr/share/icons/hicolor/scalable/apps/pdf-signer-nix.svg`;
- `/usr/share/doc/pdf-signer-nix/README.md`.

Проверки:

- запуск standalone-бинарника `--version`;
- запуск `--self-test`;
- проверка содержимого `.deb`;
- проверка наличия `.rpm`;
- создание `SHA256SUMS.txt`.

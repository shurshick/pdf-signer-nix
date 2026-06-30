# PDF Signer Nix

Linux-приложение для подписания PDF через CryptoPro CSP, добавления видимого синего штампа и создания открепленных `.sig` подписей.

Это новый проект, написанный с нуля на Python. Он не является переносом старого Go/Fyne-кода.

## Возможности

- обычное desktop-приложение на Python/Qt;
- выбор одного или нескольких PDF;
- выбор сертификата из CryptoPro CSP через `certmgr`;
- видимый синий прозрачный штамп на всех, первой, последней или указанной странице;
- базовое smart placement: поиск свободного угла без пересечения с текстом PDF;
- логотип PNG/JPG в штампе;
- встроенная PDF-подпись через `cryptcp`, если он установлен в составе CryptoPro;
- открепленная подпись `.sig` через `csptest`;
- режим "только .sig": в PDF добавляется только штамп, криптографическая подпись создается отдельным файлом;
- диагностика CryptoPro;
- проверка подписи через `csptest`;
- экспорт и импорт настроек JSON;
- логи в `$XDG_DATA_HOME/PDF Signer Nix/logs/app.log` или `~/.local/share/PDF Signer Nix/logs/app.log`;
- сборка standalone-бинарника, `.deb`, `.rpm` и `SHA256SUMS.txt`.

## Runtime Requirements

Минимальное внешнее условие: установленный CryptoPro CSP на Linux x86_64.

Ожидаемые инструменты CryptoPro:

- `/opt/cprocsp/bin/amd64/certmgr`;
- `/opt/cprocsp/bin/amd64/csptest`;
- `/opt/cprocsp/bin/amd64/cryptcp` для встроенной PDF-подписи.

Если `cryptcp` отсутствует, приложение продолжит работать для штампа и открепленной `.sig` подписи, но встроенная PDF-подпись будет недоступна.

Python и Python-библиотеки пользователю устанавливать не нужно: релизные пакеты содержат PyInstaller-бинарник.

## Запуск

```bash
pdf-signer-nix
```

Приложение откроет обычное графическое окно.

Проверка без GUI:

```bash
pdf-signer-nix --version
pdf-signer-nix --self-test
```

## Сборка

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
./scripts/build_deb.sh
./scripts/build_rpm.sh
./scripts/verify_artifacts.sh
```

## Артефакты

Релиз публикует:

- `pdf-signer-nix`;
- `pdf-signer-nix_0.1.0_amd64.deb`;
- `pdf-signer-nix-0.1.0-1.x86_64.rpm`;
- `SHA256SUMS.txt`.

## English

PDF Signer Nix is a new Python-based Linux application for signing PDFs with CryptoPro CSP, adding a visible blue stamp, and creating detached `.sig` signatures.

The release packages bundle Python and Qt dependencies into a single PyInstaller executable. The only required external runtime component is CryptoPro CSP with its command-line tools.

## License

AGPL-3.0-or-later.

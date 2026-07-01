# PDF Signer Nix

`pdf-signer-nix` - Linux desktop-приложение для подписания PDF через CryptoPro CSP. Оно ставит видимый штамп, умеет делать встроенную подпись в PDF и открепленную подпись `.sig`.

Это отдельный Python/Qt-проект с нуля. Не порт старого Go/Fyne-кода и не сервер.

## Что умеет

- подписание одного или нескольких PDF;
- drag & drop PDF, `.sig`, `.p7s`;
- выбор сертификата из CryptoPro CSP;
- встроенная подпись PDF через `cryptcp`, если он установлен;
- открепленная подпись `.sig` через `csptest`;
- режим "только `.sig`", когда в PDF остается только штамп;
- редактор штампа с профилями `ГОСТ минимальный`, `ГОСТ стандартный`, `ГОСТ подробный` и `Custom`;
- ручные координаты X/Y, перетаскивание штампа по preview и сброс позиции;
- логотип в штампе, свой текст и настройка полей;
- проверка PDF, `.sig`, `.p7s` с экспортом TXT/HTML;
- окно диагностики CryptoPro и доступ к логам;
- импорт и экспорт JSON-настроек, совместимый с Windows-версией;
- готовые артефакты: standalone binary, `.deb`, `.rpm`, `SHA256SUMS.txt`.

## Что нужно для работы

Нужен Linux x86_64 и установленный CryptoPro CSP.

Ожидаемые утилиты:

- `certmgr`
- `csptest`
- `cryptcp` для встроенной подписи PDF

Если `cryptcp` нет, приложение все равно работает для штампа, проверки и `.sig`, но встроенная подпись PDF будет недоступна.

CryptoPro в пакет не входит.

## Установка

Готовые пакеты лежат в [релизах](https://github.com/shurshick/pdf-signer-nix/releases).

DEB:

```bash
sudo dpkg -i pdf-signer-nix_0.2.9_amd64.deb
```

RPM:

```bash
sudo rpm -i pdf-signer-nix-0.2.9-1.x86_64.rpm
```

Запуск:

```bash
pdf-signer-nix
```

Проверка без GUI:

```bash
pdf-signer-nix --version
pdf-signer-nix --self-test
```

## Диагностика

Лог приложения:

```text
$XDG_DATA_HOME/PDF Signer Nix/logs/app.log
~/.local/share/PDF Signer Nix/logs/app.log
```

Если сертификаты не видны, сначала проверь:

```bash
pdf-signer-nix --self-test
certmgr -list -store uMy
certmgr -list -store mMy
```

## Сборка

Локальная разработка:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

Сборка артефактов:

```bash
./scripts/build_deb.sh
./scripts/build_rpm.sh
./scripts/verify_artifacts.sh
```

RPM собирается на EL8-совместимой базе, чтобы пакет запускался на RedOS 8 и других системах с `glibc 2.28`.

## Документация

- [CryptoPro](docs/CRYPTOPRO.md)
- [Packaging](docs/PACKAGING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](CHANGELOG.md)

## English

PDF Signer Nix is a Linux desktop application for signing PDF files with CryptoPro CSP, adding a visible stamp, and creating detached `.sig` signatures.

Release packages bundle Python and Qt into a PyInstaller binary. CryptoPro CSP is the only required external runtime dependency.

## License

AGPL-3.0-or-later.
